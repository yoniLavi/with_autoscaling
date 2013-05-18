import os
import boto
from autoscaling import Autoscaling, Policy

with Autoscaling("M2M", action="nothing") as a:
    m2masg = a.conns.asg.get_all_groups(names=["M2M"])[0]
    m2masg.health_check_type = "EC2"

