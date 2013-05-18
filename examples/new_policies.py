import os
import boto
from autoscaling import Autoscaling, Policy

with Autoscaling("MyWebApp", action="nothing") as a:
    #we create new policies, since the api doesn't allow changing the existing
    with Policy("plus-20-percent", a) as p:
        p.adjustment_type = 'PercentChangeInCapacity'
        p.scaling = 20
        p.cooldown = 900
    with Policy("minus-one-instance-cool", a) as p:
        p.adjustment_type = 'ChangeInCapacity'
        p.scaling = -1
        p.cooldown = 900

    a.create_policies()

    #just seeing that the policies were created
    pols = a.conns.asg.get_all_policies(as_group="MyWebApp")
    for pol in pols:
        print pol.name, pol.cooldown
