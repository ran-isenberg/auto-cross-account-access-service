from aws_cdk import CfnOutput, Duration, aws_apigateway
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk.aws_apigateway import AuthorizationType
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from aws_cdk.aws_logs import RetentionDays
from constructs import Construct

import cdk.demo.constants as constants


# this is the service that will be shared with other accounts, other accounts will access its API GW endpoint protected by IAM auth
class TrustServiceConstruct(Construct):
    def __init__(self, scope: Construct, id: str, common_layer: PythonLayerVersion, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        self.id_ = id
        self.lambda_role = self._build_lambda_role()
        self.common_layer = common_layer
        self.rest_api = self._build_api_gw()
        api_resource: aws_apigateway.Resource = self.rest_api.root.add_resource('api')
        orders_resource = api_resource.add_resource('order')
        self.create_order_func = self._add_post_lambda_integration(orders_resource, self.lambda_role)
        self.cross_account_access_role = self._build_cross_account_role()

    def _build_cross_account_role(self) -> iam.Role:
        role = iam.Role(
            self,
            'CrossAccountAccess',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(managed_policy_name=(f'service-role/{constants.LAMBDA_BASIC_EXECUTION_ROLE}'))
            ],
            inline_policies={
                'AllowApiInvoke': iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=['execute-api:Invoke'],
                            resources=[self.method.method_arn],
                        )
                    ]
                )
            },
        )
        CfnOutput(self, id='TrustRoleArn', value=role.role_arn).override_logical_id('TrustRoleArn')
        CfnOutput(self, id='TrustRoleName', value=role.role_name).override_logical_id('TrustRoleName')
        return role

    def _build_api_gw(self) -> aws_apigateway.RestApi:
        rest_api: aws_apigateway.RestApi = aws_apigateway.RestApi(
            self,
            'trust-service-rest-api',
            rest_api_name='Trust Service Rest API',
            description='This service handles /api/orders requests',
            deploy_options=aws_apigateway.StageOptions(throttling_rate_limit=2, throttling_burst_limit=10),
            cloud_watch_role=False,
        )

        CfnOutput(self, id='TrustApi', value=rest_api.url).override_logical_id('TrustApi')
        return rest_api

    def _build_lambda_role(self) -> iam.Role:
        return iam.Role(
            self,
            'ServiceRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(managed_policy_name=(f'service-role/{constants.LAMBDA_BASIC_EXECUTION_ROLE}'))
            ],
        )

    def _add_post_lambda_integration(
        self,
        api_resource: aws_apigateway.Resource,
        role: iam.Role,
    ) -> _lambda.Function:
        lambda_function = _lambda.Function(
            self,
            'OrdersCreateFunction',
            runtime=_lambda.Runtime.PYTHON_3_12,
            code=_lambda.InlineCode("""
                def handler(event, context):
                    print(event)
                    return {
                        'statusCode': 200,
                        'body': 'Event logged'
                    }
                """),
            handler='index.handler',
            environment={
                constants.POWERTOOLS_SERVICE_NAME: constants.SERVICE_NAME,  # for logger, tracer and metrics
                constants.POWER_TOOLS_LOG_LEVEL: 'INFO',  # for logger
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

        # POST /api/orders/ with IAM auth
        self.method = api_resource.add_method(
            http_method='POST',
            integration=aws_apigateway.LambdaIntegration(handler=lambda_function),
            authorization_type=AuthorizationType.IAM,
        )
        return lambda_function
