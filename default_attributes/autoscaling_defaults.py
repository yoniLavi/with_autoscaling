# -*- coding: utf-8 -*-
"""
This is a config file that defines the attributes and their default values
for Autoscaling DSL objects in the autoscaling module.

The attributes for the Policy sub-objects are kept in the policy_defaults file.
"""

#The following attributes must be given values (either here or in the DSL)
zones = ['us-east-1b']
min_size = 0
max_size = 3
ami = 'ami-8baa73e2'
access_key = 'default'
security_groups = ['default']
instance_type = 'm1.small'
create_load_balancer = True
listeners = [(80, 8080, 'http')]
health_check_target = 'HTTP:80/index.html'
health_check_interval = 20
health_check_timeout = 3
health_check_period = 600
health_check_type = "EC2"
instance_monitoring = True


user_data = None  # should be left at None if you don't need user-data

# The following attributes have defaults dependent on other attributes, so you
# can safely leave them at None
load_balancer_name = None  # defaults to "<ASGROUP>-lb"
launch_config_name = None  # defaults to "<ASGROUP>-lc"
name_tag = None  # defaults to "<ASGROUP> Auto"
