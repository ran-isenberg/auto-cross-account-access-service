#!/usr/bin/env python3
import os

from aws_cdk import App, Environment
from boto3 import client, session

from cdk.demo.stack import ServiceStack
from cdk.demo.utils import get_stack_name

account = client('sts').get_caller_identity()['Account']
region = session.Session().region_name
app = App()
my_stack = ServiceStack(
    scope=app,
    id=get_stack_name(),
    env=Environment(account=os.environ.get('AWS_DEFAULT_ACCOUNT', account), region=os.environ.get('AWS_DEFAULT_REGION', region)),
)

app.synth()
