import aws_cdk.aws_lambda_event_sources as eventsources
import boto3
from aws_cdk import CfnOutput, Duration, RemovalPolicy, aws_sns, aws_sqs
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_sns_subscriptions as subscriptions
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from aws_cdk.aws_logs import RetentionDays
from constructs import Construct

import cdk.demo.constants as constants
from cdk.demo.catalog.governance_db_construct import GovernanceDbConstruct


class GovernanceConstruct(Construct):
    def __init__(self, scope: Construct, id_: str, common_layer: PythonLayerVersion, service_trust_role: iam.Role) -> None:
        super().__init__(scope, id_)
        self.id_ = id_
        self.api_db = GovernanceDbConstruct(self, f'{id_}db')
        self.lambda_role = self._build_lambda_role(self.api_db.db, service_trust_role)
        self.common_layer = common_layer
        self.governance_lambda = self._build_governance_lambda(self.lambda_role, self.api_db.db, self.common_layer, service_trust_role)
        self.sns_topic = self._build_sns()
        self.queue = self._build_sns_sqs_lambda_pattern(self.sns_topic, self.governance_lambda)
        self._set_outputs()

    def _set_outputs(self) -> None:
        CfnOutput(self, 'ServiceRoleArn', value=self.lambda_role.role_arn).override_logical_id('ServiceRoleArn')
        CfnOutput(self, 'ServiceRoleName', value=self.lambda_role.role_name).override_logical_id('ServiceRoleName')

    def _build_sns(self) -> aws_sns.Topic:
        topic = aws_sns.Topic(
            self,
            f'{self.id_}{constants.SNS_TOPIC}',
            display_name=f'{self.id_}{constants.SNS_TOPIC}',
            topic_name=f'{self.id_}{constants.SNS_TOPIC}',
        )
        # Define the policy statement to allow all principals in the organization to publish to the topic
        policy_statement = iam.PolicyStatement(actions=['sns:Publish'], resources=[topic.topic_arn], principals=[iam.AnyPrincipal()])

        # Add a condition to the policy statement to restrict to the organization
        client = boto3.client('organizations')
        response = client.describe_organization()
        policy_statement.add_condition(
            'StringEquals',
            {
                'aws:PrincipalOrgID': response['Organization']['Id'],
            },
        )

        # Attach the policy statement to the topic
        topic.add_to_resource_policy(policy_statement)
        return topic

    def _build_sns_sqs_lambda_pattern(self, topic: aws_sns.Topic, function: _lambda.Function) -> aws_sqs.Queue:
        dlq = aws_sqs.Queue(self, 'dlq', visibility_timeout=Duration.seconds(300), retention_period=Duration.days(1))
        queue = aws_sqs.Queue(
            self,
            f'{self.id_}{constants.SQS}',
            visibility_timeout=Duration.seconds(300),
            retention_period=Duration.days(1),
            queue_name=f'{self.id_}{constants.SQS}',
            removal_policy=RemovalPolicy.DESTROY,
            encryption=aws_sqs.QueueEncryption.SQS_MANAGED,
            dead_letter_queue=aws_sqs.DeadLetterQueue(max_receive_count=3, queue=dlq),
        )
        topic.add_subscription(topic_subscription=subscriptions.SqsSubscription(queue, raw_message_delivery=True))
        function.add_event_source(eventsources.SqsEventSource(queue=queue, batch_size=1, enabled=True))
        # todo add DLQ redrive pattern
        return queue

    def _build_lambda_role(self, db: dynamodb.TableV2, service_trust_role: iam.Role) -> iam.Role:
        return iam.Role(
            self,
            'governRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            inline_policies={
                'dynamodb_db': iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=['dynamodb:PutItem', 'dynamodb:GetItem', 'dynamodb:DeleteItem'],
                            resources=[db.table_arn],
                            effect=iam.Effect.ALLOW,
                        )
                    ]
                ),
                'trust_relationship': iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=['iam:UpdateAssumeRolePolicy', 'iam:GetRole'],
                            resources=[service_trust_role.role_arn],
                            effect=iam.Effect.ALLOW,
                        )
                    ]
                ),
            },
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(managed_policy_name=(f'service-role/{constants.LAMBDA_BASIC_EXECUTION_ROLE}'))
            ],
        )

    def _build_governance_lambda(
        self,
        role: iam.Role,
        db: dynamodb.TableV2,
        layer: PythonLayerVersion,
        service_trust_role: iam.Role,
    ) -> _lambda.Function:
        lambda_function = _lambda.Function(
            self,
            constants.VISIBILITY_LAMBDA,
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset(constants.BUILD_FOLDER),
            handler='catalog_backend.handlers.product_callback_handler.handle_product_event',
            environment={
                constants.POWERTOOLS_SERVICE_NAME: constants.SERVICE_NAME,  # for logger, tracer and metrics
                constants.POWER_TOOLS_LOG_LEVEL: 'INFO',  # for logger
                'POWERTOOLS_METRICS_NAMESPACE': constants.METRICS_NAMESPACE,  # for metrics
                'METRICS_DIMENSION_KEY': constants.METRICS_DIMENSION_VALUE,  # for metrics
                'TABLE_NAME': db.table_name,
                'SERVICE_ROLE_NAME': service_trust_role.role_name,
                'SERVICE_ROLE_ARN': service_trust_role.role_arn,
                # 'PORTFOLIO_ID': constants.PORTFOLIO_ID, is added later after portfolio creation
            },
            tracing=_lambda.Tracing.ACTIVE,
            retry_attempts=0,
            timeout=Duration.seconds(constants.API_HANDLER_LAMBDA_TIMEOUT),
            memory_size=constants.API_HANDLER_LAMBDA_MEMORY_SIZE,
            layers=[layer],
            role=role,
            log_retention=RetentionDays.ONE_DAY,
            log_format=_lambda.LogFormat.JSON.value,
            system_log_level=_lambda.SystemLogLevel.WARN.value,
        )

        return lambda_function
