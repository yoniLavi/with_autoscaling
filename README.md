# With_Autoscaling: A chef-like DSL for creation of AWS autoscaling entities.

The idea is to have an easy way to declaratively set up similar autoscaling groups
(with attached load balancer and launch config) for quickly creating staging environments etc.

## Usage

Usage example:

    from autoscaling import Autoscaling, Policy

    with Autoscaling("MyWebApp", action="create_if_missing") as a:
        a.zones = ['us-east-1b']
        a.load_balancer = 'myapp-MyWebApp-lb'
        a.min_size = 0
        a.max_size = 3
        a.user_data = open('cloudinitMyWebApp', 'r').read()

        with Policy("plus-one-instance", a) as p:
            p.adjustment_type = 'ChangeInCapacity'
            p.scaling = 1
            p.cooldown = 180

Default values will be provided for all missing attributes, except for the
autoscaling group's name which is entered as the object's name.
The possible actions are "create_if_missing", "create_with_overwrite",
"delete" and "nothing", with "create_if_missing" being the default.

The action "create_if_missing" will fail with an exception of type
AlreadyExistsError if previous versions of the entities to
be created (autoscaling group, load balancer etc...) already exist.

The inner conns object allows use of the ELBConnection as elb and
AutoScaleConnection as asg for basic logic inside
the DSL. For most usage patterns these can be ignored.

Note that I chose not to implement forced deletion of autoscaling
groups in case there are active instances. Please use a separate api call
to empty the autoscaling group before deleting/overwriting it.

See more under the examples directory.

## License

Apache v2

## Author

Yoni Lavi - yoni@lavi.fm, created during my time at fewbytes.com
