from aws_cdk import Aspects, RemovalPolicy, Stack, Tags
from aws_cdk import aws_lambda as _lambda
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from cdk_nag import AwsSolutionsChecks, NagSuppressions
from constructs import Construct

import cdk.demo.constants as constants
from cdk.demo.catalog.governance_construct import GovernanceConstruct
from cdk.demo.catalog.observability_construct import ObservabilityConstruct
from cdk.demo.catalog.portfolio_construct import PortfolioConstruct
from cdk.demo.constants import OWNER_TAG, SERVICE_NAME, SERVICE_NAME_TAG
from cdk.demo.demo_construct import DemoConstruct
from cdk.demo.trust_service import TrustServiceConstruct
from cdk.demo.utils import get_construct_name, get_username


class ServiceStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        self._add_stack_tags()
        self.common_layer = self._build_common_layer()
        self.trust_service = TrustServiceConstruct(
            self,
            get_construct_name(stack_prefix=id, construct_name='TrustService'),
            common_layer=self.common_layer,
        )
        self.governance = GovernanceConstruct(
            self,
            get_construct_name(stack_prefix=id, construct_name='Governance'),
            self.common_layer,
            self.trust_service.cross_account_access_role,
        )
        self.portfolio = PortfolioConstruct(
            self,
            get_construct_name(stack_prefix=id, construct_name='Portfolio'),
            self.governance.sns_topic,
            self.governance.governance_lambda,
        )
        self.observability = ObservabilityConstruct(
            self,
            get_construct_name(stack_prefix=id, construct_name='Observability'),
            db=self.governance.api_db.db,
            functions=[self.governance.governance_lambda],
            visibility_queue=self.governance.queue,
            visibility_topic=self.governance.sns_topic,
        )

        self.demo_construct = DemoConstruct(
            self,
            get_construct_name(stack_prefix=id, construct_name='Demo'),
            self.common_layer,
            self.trust_service.rest_api.url,
            self.trust_service.cross_account_access_role.role_arn,
        )

        # add security check
        self._add_security_tests()

    def _build_common_layer(self) -> PythonLayerVersion:
        return PythonLayerVersion(
            self,
            constants.LAMBDA_LAYER_NAME,
            entry=constants.COMMON_LAYER_BUILD_FOLDER,
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_13],
            removal_policy=RemovalPolicy.DESTROY,
        )

    def _add_stack_tags(self) -> None:
        # best practice to help identify resources in the console
        Tags.of(self).add(SERVICE_NAME_TAG, SERVICE_NAME)
        Tags.of(self).add(OWNER_TAG, get_username())

    def _add_security_tests(self) -> None:
        Aspects.of(self).add(AwsSolutionsChecks(verbose=True))
        # Suppress a specific rule for this resource
        NagSuppressions.add_stack_suppressions(
            self,
            [
                {'id': 'AwsSolutions-IAM4', 'reason': 'policy for cloudwatch logs.'},
                {'id': 'AwsSolutions-IAM5', 'reason': 'policy for cloudwatch logs.'},
                {'id': 'AwsSolutions-APIG2', 'reason': 'lambda does input validation'},
                {'id': 'AwsSolutions-APIG1', 'reason': 'not mandatory in a sample template'},
                {'id': 'AwsSolutions-APIG3', 'reason': 'not mandatory in a sample template'},
                {'id': 'AwsSolutions-APIG6', 'reason': 'not mandatory in a sample template'},
                {'id': 'AwsSolutions-APIG4', 'reason': 'authorization not mandatory in a sample template'},
                {'id': 'AwsSolutions-COG4', 'reason': 'not using cognito'},
                {'id': 'AwsSolutions-L1', 'reason': 'False positive'},
                {'id': 'AwsSolutions-SNS2', 'reason': 'ignored for now'},
                {'id': 'AwsSolutions-SNS3', 'reason': 'False positive'},
                {'id': 'AwsSolutions-SQS4', 'reason': 'False positive'},
            ],
        )
