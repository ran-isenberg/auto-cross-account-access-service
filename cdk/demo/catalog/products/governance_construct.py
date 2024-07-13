from typing import Optional

from aws_cdk import CfnOutput, CfnParameter, CustomResource, RemovalPolicy, Stack, Token, aws_sns
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
        CfnOutput(self, id='AssumeRoleArn', value=assume_role_arn, description='The role you need to assume').override_logical_id('AssumeRoleArn')
        CfnOutput(self, id='LambdaRoleArn', value=trust_role_arn, description='The Lambda role to use').override_logical_id('LambdaRoleArn')
        """ computed_name = PARAMETER_NAME_TEMPLATE.format(
            consumer_name=self._consumer_name,
            env_name=self._deploy_env_name,
            product_name=self._product_name,
            key=key,
        )
        StringParameter(
            self,
            f'ProductParam-{key.replace("/", "").replace("-", "")}',
            description=f'An output parameter of a portfolio product. Product={self._product_name}',
            parameter_name=computed_name,
            string_value=value,
            simple_name=False,
            tier=ParameterTier.STANDARD,
        ) """
