from autoscaling import Autoscaling, Policy

with Autoscaling("MyWebApp", action="create_with_overwrite") as a:
    a.region = 'us-east-1'
    a.zones = ['us-east-1b']
    a.min_size = 0
    a.max_size = 3
    a.ami = 'ami-8baa73e2'
    a.access_key = 'AWS'
    a.security_groups = ['MyWebApp']
    a.instance_type = 'm1.small'

    #enable this if you're using custom userdata
    #a.user_data = open('cloudinitMyWebApp', 'r').read()

    with Policy("plus-one-instance", a) as p:
        p.adjustment_type = 'ChangeInCapacity'
        p.scaling = 1
    with Policy("minus-one-instance", a) as p:
        p.adjustment_type = 'ChangeInCapacity'
        p.scaling = -1
