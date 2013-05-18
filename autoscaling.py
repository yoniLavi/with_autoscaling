"""
A chef-like DSL for creation of AWS autoscaling entities.

2012 - yoni@fewbytes.com
"""

import os

import boto.ec2
import boto.ec2.elb
from boto.ec2.elb import ELBConnection
from boto.ec2.elb import HealthCheck
from boto.ec2.autoscale import AutoScaleConnection
from boto.ec2.autoscale import LaunchConfiguration
from boto.ec2.autoscale import AutoScalingGroup
from boto.ec2.autoscale import ScalingPolicy
from boto.ec2.autoscale.tag import Tag

from default_attributes import autoscaling_defaults, policy_defaults


class AlreadyExistsError(Exception):
    """An exception for when an autoscaling entity with the requested name
    already exists"""
    def __init__(self, entity_name):
        Exception.__init__(self)
        self.entity_name = entity_name

    def __str__(self):
        return ('The entity %s already exists.\n' % self.entity_name +
                'Consider using action="create_with_overwrite".')


class BotoConns(object):
    """A helper class to hold boto api connections to AWS"""
    def __init__(self, region_name):
         #load credentials from env variables
        credential_vars = ['AWS_ACCESS_KEY', 'AWS_SECRET_KEY']
        try:
            access_key, secret_key = [os.environ[var]
                                        for var in credential_vars]
        except KeyError:
            raise Exception("You must export the following environment " +
                            "variables: %s" % ", ".join(credential_vars))

        elb_region = next(r for r in boto.ec2.elb.regions()
                                    if r.name == region_name)
        asg_region = next(r for r in boto.ec2.autoscale.regions()
                                    if r.name == region_name)

        self.elb = ELBConnection(
                    access_key, secret_key, region=elb_region)
        self.asg = AutoScaleConnection(
                    access_key, secret_key, region=asg_region)


class Autoscaling(object):
    """Allows creation of an AWS autoscaling group and associated entities
    via a chef-like DSL using the "with" statement.

    Usage example:
        with Autoscaling("MyWebApp", action="create_if_missing") as a:
            a.zones = ['us-east-1b']
            a.load_balancer = 'myapp-MyWebApp-lb'
            a.min_size = 0
            a.max_size = 3
    """
    def __init__(self, name, region="us-east-1", action="create_if_missing"):
        #general attributes
        self.name = name
        self.action = action
        self.policies = []

        #import default attributes
        self.dsl_elems = autoscaling_defaults

        #open boto connections to AWS
        self.conns = BotoConns(region)

        #expose additional objects to the DSL
        self.dsl_elems.name = self.name
        self.dsl_elems.add_policy = self.add_policy
        self.dsl_elems.conns = self.conns

        #these will be filled inside the actions
        self.health_check = None
        self.load_balancer = None
        self.launch_config = None
        self.auto_scaling_group = None

    def __enter__(self):
        return self.dsl_elems

    def __exit__(self, exit_type, value, callback):
        #generate dependent attribute defaults
        if not self.dsl_elems.load_balancer_name:
            self.dsl_elems.load_balancer_name = self.name + "-lb"
        if not self.dsl_elems.launch_config_name:
            self.dsl_elems.launch_config_name = self.name + "-lc"
        if not self.dsl_elems.name_tag:
            self.dsl_elems.name_tag = self.name + " Auto"

        if self.action == "delete":
            self.delete_all()
            return
        if self.action == "create_if_missing":
            self.create_all()
            return
        if self.action == "create_with_overwrite":
            self.delete_all()
            self.create_all()
            return
        if self.action == "nothing":
            return
        raise Exception("Action '%s' is unrecognized" % self.action)

    def delete_all(self):
        """Delete all the autoscaling entities that are named as
        defined in the attributes

        I would have liked to use boto's name parameter in the get_all
        methods to only search for my objects instead of bringing them all,
        but for some reason, failure to find an object in such a case returns
        a 400 HTTP response leading to ResponseError;
        and I'm not in the mood of catching and parsing it.
        """
        if self.dsl_elems.load_balancer_name in ([lb.name for lb
                                in self.conns.elb.get_all_load_balancers()]):
            self.conns.elb.delete_load_balancer(
                                self.dsl_elems.load_balancer_name)

        if self.name in ([as_group.name for as_group
                                in self.conns.asg.get_all_groups()]):
            self.conns.asg.delete_auto_scaling_group(self.name)

        if self.dsl_elems.launch_config_name in (
            [lc.name for lc in
                self.conns.asg.get_all_launch_configurations()]):
            self.conns.asg.delete_launch_configuration(
                                self.dsl_elems.launch_config_name)

    def create_load_balancer(self):
        """Create a load balancer for this autoscaling group

        http://docs.pythonboto.org/en/latest/ref/elb.html
        """
        lb_names = [lb.name for lb
                    in self.conns.elb.get_all_load_balancers()]
        if self.dsl_elems.load_balancer_name in lb_names:
            raise AlreadyExistsError(self.dsl_elems.load_balancer_name)

        self.health_check = HealthCheck(
           'healthCheck',
           interval=self.dsl_elems.health_check_interval,
           target=self.dsl_elems.health_check_target,
           timeout=self.dsl_elems.health_check_timeout
        )

        self.load_balancer = self.conns.elb.create_load_balancer(
            name=self.dsl_elems.load_balancer_name,
            zones=self.dsl_elems.zones,
            listeners=self.dsl_elems.listeners
        )

        self.load_balancer.configure_health_check(self.health_check)

    def create_launch_config(self):
        """Create the launch configuration

        http://docs.pythonboto.org/en/latest/ref/autoscale.html
        """
        lc_names = [lc.name for lc
                    in self.conns.asg.get_all_launch_configurations()]
        if self.dsl_elems.launch_config_name in lc_names:
            raise AlreadyExistsError(self.dsl_elems.launch_config_name)

        self.launch_config = LaunchConfiguration(
            name=self.dsl_elems.launch_config_name,
            image_id=self.dsl_elems.ami,
            key_name=self.dsl_elems.access_key,
            security_groups=self.dsl_elems.security_groups,
            instance_type=self.dsl_elems.instance_type,
            instance_monitoring=self.dsl_elems.instance_monitoring,
            user_data=self.dsl_elems.user_data)
        self.conns.asg.create_launch_configuration(self.launch_config)

    def create_autoscaling_group(self):
        """Create the launch configuration and autoscaling group.

        http://docs.pythonboto.org/en/latest/ref/autoscale.html
        """
        if self.name in ([as_group.name for as_group
                          in self.conns.asg.get_all_groups()]):
            raise AlreadyExistsError(self.name)

        lb_list = []
        if self.dsl_elems.create_load_balancer:
            lb_list.append(self.dsl_elems.load_balancer_name)

        self.auto_scaling_group = AutoScalingGroup(
            group_name=self.name,
            load_balancers=lb_list,
            availability_zones=self.dsl_elems.zones,
            launch_config=self.launch_config,
            min_size=self.dsl_elems.min_size,
            max_size=self.dsl_elems.max_size,
            health_check_period=self.dsl_elems.health_check_period,
            health_check_type=self.dsl_elems.health_check_type
        )

        self.conns.asg.create_auto_scaling_group(self.auto_scaling_group)
        self.conns.asg.create_or_update_tags([
            Tag(connection=self.conns.asg,
                key='Name',
                value=self.dsl_elems.name_tag,
                resource_id=self.name,
                propagate_at_launch=True)
        ])

    def add_policy(self, policy):
        """Add a policy to be created for this autoscaling group
        """
        self.policies.append(policy)

    def create_policies(self):
        """Create the autoscaling policies for this autoscaling group
        """
        for policy in self.policies:
            self.conns.asg.create_scaling_policy(policy)

    def create_all(self):
        """Create the AWS autoscaling entities with the attributes defined
        in self.
        """
        #Create the entities
        print "starting creation of %s" % self.name
        if self.dsl_elems.create_load_balancer:
            self.create_load_balancer()
        self.create_launch_config()
        self.create_autoscaling_group()
        self.create_policies()

        #epilogue
        print "Operation finished successfully"
        if self.dsl_elems.create_load_balancer:
            print ("Map the CNAME of your website to: %s"
                    % self.load_balancer.dns_name)


class Policy(object):
    """Allows creation of an AWS autoscaling policy in a given autoscaling
    group using a chef-like DSL "with" statement.

    Usage example:
        with Autoscaling("MyWebApp") as a:
            ...
            with Policy("plus-one-instance", a) as p:
                p.adjustment_type = 'ChangeInCapacity'
                p.scaling = 1
                p.cooldown = 180
    """
    def __init__(self, name, autoscaling_group):
        #general attributes
        self.name = name
        self.autoscaling_group = autoscaling_group

        #import default attributes
        self.dsl_elems = policy_defaults

    def __enter__(self):
        return self.dsl_elems

    def __exit__(self, exit_type, value, callback):
        self.create()

    def create(self):
        """Add the AWS autoscaling policy defined in self.

        The creation itself will be performed in the AutoScaling object.
        """
        self.autoscaling_group.add_policy(
            ScalingPolicy(
                name=self.name,
                as_name=self.autoscaling_group.name,
                adjustment_type=self.dsl_elems.adjustment_type,
                scaling_adjustment=self.dsl_elems.scaling,
                cooldown=self.dsl_elems.cooldown))
