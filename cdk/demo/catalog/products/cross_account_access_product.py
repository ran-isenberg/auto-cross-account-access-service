from aws_cdk import aws_iam as iam
from aws_cdk import aws_servicecatalog as servicecatalog
from aws_cdk import aws_sns
from constructs import Construct

from cdk.demo.catalog.products.governance_product_construct import GovernanceProductConstruct


class CrossAccountAccessProduct(servicecatalog.ProductStack):
    PRODUCT_NAME = 'Service X - Cross Account Access'
    PRODUCT_VERSION = '1.0.0'
    DESCRIPTION = 'An IAM role to assume to gain cross account access to service X IAN protected resources'

    def __init__(
        self,
        scope: Construct,
        id: str,
        topic: aws_sns.Topic,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)
        self.product_description = CrossAccountAccessProduct.DESCRIPTION
        self.product_name = CrossAccountAccessProduct.PRODUCT_NAME
        self.product_version = CrossAccountAccessProduct.PRODUCT_VERSION

        # Create the IAM role within the product stack
        self.role = iam.Role(
            self,
            'TrustRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com'),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name('AWSCloudFormationFullAccess'),
                iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess'),
            ],
        )

        self.governance_enabler = GovernanceProductConstruct(
            self,
            'GovernanceEnabler',
            topic,
            self.product_name,
            self.product_version,
            self.role.role_arn,
        )
        self.governance_enabler.node.add_dependency(self.role)
