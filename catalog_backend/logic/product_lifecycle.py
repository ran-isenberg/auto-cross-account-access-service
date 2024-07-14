from typing import Optional

from aws_lambda_env_modeler import get_environment_variables

from catalog_backend.dal import get_dal_handler
from catalog_backend.dal.db_handler import DalHandler
from catalog_backend.handlers.models.env_vars import VisibilityEnvVars
from catalog_backend.handlers.utils.observability import logger, tracer
from catalog_backend.logic.iam.iam_manager import create_iam_trust, delete_iam_trust, update_iam_trust
from catalog_backend.models.input import ProductCreateEventModel, ProductDeleteEventModel, ProductUpdateEventModel


# return the request_id of the product which will be used as the custom resource logical id
@tracer.capture_method(capture_response=False)
def provision_product(
    product_details: ProductCreateEventModel,
) -> tuple[str, Optional[dict]]:
    env_vars = get_environment_variables(model=VisibilityEnvVars)
    cfn_data = None
    if product_details.resource_properties.trust_role_arn:
        logger.info('trust role arn is provided, creating trust policy', trust_role_arn=product_details.resource_properties.trust_role_arn)
        external_id = create_iam_trust(
            service_role_name=env_vars.SERVICE_ROLE_NAME,
            product_role_arn=product_details.resource_properties.trust_role_arn,
        )
        cfn_data = {'assume_role_arn': env_vars.SERVICE_ROLE_ARN, 'external_id': external_id}

    # finish creation
    dal_handler: DalHandler = get_dal_handler(env_vars.TABLE_NAME)
    dal_handler.add_product_deployment(
        portfolio_id=env_vars.PORTFOLIO_ID,
        product_stack_id=product_details.stack_id,
        product_name=product_details.resource_properties.product_name,
        product_version=product_details.resource_properties.product_version,
        account_id=product_details.resource_properties.account_id,
        consumer_name=product_details.resource_properties.consumer_name,
        region=product_details.resource_properties.region,
    )
    return product_details.request_id, cfn_data


@tracer.capture_method(capture_response=False)
def delete_product(product_details: ProductDeleteEventModel) -> None:
    env_vars = get_environment_variables(model=VisibilityEnvVars)
    dal_handler: DalHandler = get_dal_handler(env_vars.TABLE_NAME)

    if product_details.resource_properties.trust_role_arn:
        logger.info('trust role arn is provided, deleting trust policy', trust_role_arn=product_details.resource_properties.trust_role_arn)
        delete_iam_trust(
            service_role_name=env_vars.SERVICE_ROLE_NAME,
            product_role_arn=product_details.resource_properties.trust_role_arn,
        )
    # finish deletion
    dal_handler.delete_product_deployment(env_vars.PORTFOLIO_ID, product_details.stack_id)


@tracer.capture_method(capture_response=False)
def update_product(product_details: ProductUpdateEventModel) -> Optional[dict]:
    env_vars = get_environment_variables(model=VisibilityEnvVars)
    cfn_data = None
    if product_details.resource_properties.trust_role_arn:
        logger.info('trust role arn is provided, updating trust policy', trust_role_arn=product_details.resource_properties.trust_role_arn)
        external_id = update_iam_trust(
            service_role_name=env_vars.SERVICE_ROLE_NAME,
            product_role_arn=product_details.resource_properties.trust_role_arn,
            old_product_role_arn=product_details.old_resource_properties.trust_role_arn,  # type: ignore
        )
        cfn_data = {'assume_role_arn': env_vars.SERVICE_ROLE_ARN, 'external_id': external_id}

    dal_handler: DalHandler = get_dal_handler(env_vars.TABLE_NAME)
    dal_handler.update_product_deployment(
        portfolio_id=env_vars.PORTFOLIO_ID,
        product_stack_id=product_details.stack_id,
        product_name=product_details.resource_properties.product_name,
        product_version=product_details.resource_properties.product_version,
        account_id=product_details.resource_properties.account_id,
        consumer_name=product_details.resource_properties.consumer_name,
        region=product_details.resource_properties.region,
    )
    return cfn_data
