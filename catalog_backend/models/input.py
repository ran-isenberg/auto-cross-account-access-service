from typing import Literal, Optional

from aws_lambda_powertools.utilities.parser.models import (
    CloudFormationCustomResourceCreateModel,
    CloudFormationCustomResourceDeleteModel,
    CloudFormationCustomResourceUpdateModel,
)
from pydantic import BaseModel, Field


class ProductModel(BaseModel):
    product_name: str = Field(..., min_length=1, max_length=40, alias='product_name')
    product_version: str = Field(..., min_length=1, max_length=10, alias='product_version')
    account_id: str = Field(..., min_length=1, max_length=40, alias='account_id')
    consumer_name: str = Field(..., min_length=1, max_length=40, alias='consumer_name')
    region: str = Field(..., min_length=1, max_length=20, alias='region')
    trust_role_arn: Optional[str] = Field(None, min_length=1, alias='trust_role_arn')


class ProductCreateEventModel(CloudFormationCustomResourceCreateModel):
    resource_properties: ProductModel = Field(..., alias='ResourceProperties')
    resource_type: Literal['Custom::PlatformEngGovernanceEnabler'] = Field(..., alias='ResourceType')


class ProductDeleteEventModel(CloudFormationCustomResourceDeleteModel):
    resource_properties: ProductModel = Field(..., alias='ResourceProperties')
    resource_type: Literal['Custom::PlatformEngGovernanceEnabler'] = Field(..., alias='ResourceType')


class ProductUpdateEventModel(CloudFormationCustomResourceUpdateModel):
    resource_properties: ProductModel = Field(..., alias='ResourceProperties')
    old_resource_properties: ProductModel = Field(..., alias='OldResourceProperties')
    resource_type: Literal['Custom::PlatformEngGovernanceEnabler'] = Field(..., alias='ResourceType')
