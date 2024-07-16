import json
from typing import Optional

from aws_cdk import CfnOutput, CfnParameter, CustomResource, RemovalPolicy, Stack, Token, aws_sns
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from cdk.demo.constants import CUSTOM_RESOURCE_TYPE


class GovernanceProductConstruct(Construct):
    ## This construct is used to create a custom resource that will be used to enable governance for a product
    ## The custom resource will be triggered by an SNS topic
    ## The custom resource will take in the product name, product version, and consumer name as parameters
    ## The custom resource will be responsible for creating the necessary resources to enable governance for the product
    def __init__(
        self,
        scope: Construct,
        id: str,
        topic: aws_sns.Topic,
        product_name: str,
        product_version: str,
        trust_role_arn: Optional[str] = None,
    ) -> None:
        super().__init__(scope, id)
        # Add a parameter for consumer_name
        self.consumer_name_param = CfnParameter(
            self,
            id='ConsumerName',
            type='String',
            description='Name of the team that deployed the product',
            min_length=1,
        )
        self.consumer_name_param.override_logical_id('ConsumerName')  # this will be the parameter name in the CloudFormation template
        self.custom_resource = self._create_custom_resource(
            topic, product_name, product_version, self.consumer_name_param.value_as_string, trust_role_arn
        )

    def _create_custom_resource(
        self, topic: aws_sns.Topic, product_name: str, product_version: str, consumer_name: str, trust_role_arn: Optional[str]
    ) -> CustomResource:
        stack = Stack.of(self)
        cr_end_props = {
            'account_id': stack.account,
            'region': stack.region,
            'product_name': product_name,
            'product_version': product_version,
            'consumer_name': consumer_name,
            'trust_role_arn': trust_role_arn or None,
        }
        custom_resource = CustomResource(
            self,
            'PlatformGovernanceCustomResource',
            service_token=topic.topic_arn,
            resource_type=CUSTOM_RESOURCE_TYPE,
            removal_policy=RemovalPolicy.DESTROY,
            properties=cr_end_props,
        )
        if trust_role_arn:
            self._publish_cross_account_params(product_name, product_version, consumer_name, custom_resource, trust_role_arn)
        return custom_resource

    def _publish_cross_account_params(
        self,
        product_name: str,
        product_version: str,
        consumer_name: str,
        custom_resource: CustomResource,
        trust_role_arn: str,
    ) -> None:
        assume_role_arn = Token.as_string(custom_resource.get_att_string('assume_role_arn'))
        external_id = Token.as_string(custom_resource.get_att_string('external_id'))
        CfnOutput(
            self, id='OrdersRoleArn', value=assume_role_arn, description='The role you need to assume to gain access to orders service'
        ).override_logical_id('OrdersRoleArn')
        CfnOutput(self, id='MediatorRoleArn', value=trust_role_arn, description='The mediator role to assume').override_logical_id('MediatorRoleArn')
        CfnOutput(
            self, id='OrdersExternalId', value=external_id, description='The external Id you use when you assume the orders role'
        ).override_logical_id('OrdersExternalId')

        ssm_value = {'ordersAssumeRoleArn': assume_role_arn, 'ordersExternalId': external_id, 'mediatorRoleArn': trust_role_arn}

        ssm.StringParameter(
            self,
            'ordersAssumeRoleArn',
            description='contains role arn, external id to assume to access orders API and the mediator role ARN to assume',
            parameter_name=f'/orders/{consumer_name}/{product_version}',
            string_value=json.dumps(ssm_value),
            simple_name=False,
            tier=ssm.ParameterTier.STANDARD,
        )
