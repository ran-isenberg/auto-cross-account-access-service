from aws_cdk import CfnOutput, Duration
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from aws_cdk.aws_logs import RetentionDays
from constructs import Construct

import cdk.demo.constants as constants


# this lambda is used to invoke after the product is deployed
class DemoConstruct(Construct):
    def __init__(self, scope: Construct, id: str, common_layer: PythonLayerVersion, api_url: str, assume_role_arn: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        self.id_ = id
        self.lambda_role = self._build_lambda_role()
        self.common_layer = common_layer
        self.create_order_func = self._build_demo_lambda(self.lambda_role, api_url, assume_role_arn)

    def _build_lambda_role(self) -> iam.Role:
        return iam.Role(
            self,
            'ServiceRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(managed_policy_name=(f'service-role/{constants.LAMBDA_BASIC_EXECUTION_ROLE}'))
            ],
            inline_policies={
                'AllowAssumeRole': iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=['sts:AssumeRole'],
                            resources=['*'],
                        )
                    ]
                ),
                'AllowSSMGetParameters': iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=['ssm:GetParameter'],
                            resources=['*'],
                        )
                    ]
                ),
            },
        )

    def _build_demo_lambda(self, role: iam.Role, api_url: str, assume_role_arn: str) -> _lambda.Function:
        function = _lambda.Function(
            self,
            'DemoFunction',
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.Code.from_asset(constants.DEMO_FOLDER),
            handler='demo.handlers.handler.lambda_handler',
            environment={
                constants.POWERTOOLS_SERVICE_NAME: 'demo',  # for logger, tracer and metrics
                constants.POWER_TOOLS_LOG_LEVEL: 'INFO',  # for logger
                'API_URL': api_url,
                'PRODUCT_VERSION': '1.0.0',
                'CONSUMER_NAME': 'ran',  # this will be used to find the path in the SSM parameter store to get all the role ARNs to assume
            },
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            timeout=Duration.seconds(constants.API_HANDLER_LAMBDA_TIMEOUT),
            memory_size=constants.API_HANDLER_LAMBDA_MEMORY_SIZE,
            layers=[self.common_layer],
            role=role,
            log_retention=RetentionDays.ONE_DAY,
            log_format=_lambda.LogFormat.JSON.value,
            system_log_level=_lambda.SystemLogLevel.INFO.value,
        )
        CfnOutput(self, id='DemoLambda', value=function.function_name).override_logical_id('DemoLambda')
        return function
