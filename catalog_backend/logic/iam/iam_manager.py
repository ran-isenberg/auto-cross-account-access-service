import boto3

from catalog_backend.handlers.utils.observability import tracer
from catalog_backend.logic.iam.helpers import (
    clean_statements,
    create_statement_and_external_id,
    get_trust_policy,
    update_assume_role_policy,
)


# returns external id for the trust policy
@tracer.capture_method(capture_response=False)
def create_iam_trust(service_role_name: str, product_role_arn: str) -> str:
    iam_client = boto3.client('iam')
    current_policy_document = get_trust_policy(iam_client, service_role_name)

    # Check if the product_role_arn is already in the trust policy
    new_statements = []
    external_id = None
    for statement_item in current_policy_document.get('Statement', []):
        principal_arn = statement_item.get('Principal', {}).get('AWS')
        if principal_arn == product_role_arn:
            external_id = statement_item['Condition']['StringEquals']['sts:ExternalId']
        new_statements.append(statement_item)

    # product_role_arn and external_id didn't exists before, add a new statement
    if not external_id:
        new_statement, external_id = create_statement_and_external_id(product_role_arn)
        new_statements.append(new_statement)

    # Update the trust policy, replace statements with new_statements
    current_policy_document['Statement'] = new_statements
    update_assume_role_policy(iam_client, service_role_name, current_policy_document)
    return external_id


# returns external id for the trust policy, updates policy if needed
@tracer.capture_method(capture_response=False)
def update_iam_trust(service_role_name: str, product_role_arn: str, old_product_role_arn: str) -> str:
    iam_client = boto3.client('iam')
    current_policy_document = get_trust_policy(iam_client, service_role_name)

    new_statements = clean_statements(current_policy_document.get('Statement', []), old_product_role_arn)
    new_statement, external_id = create_statement_and_external_id(product_role_arn)
    new_statements.append(new_statement)

    # replace statements with new_statements
    current_policy_document['Statement'] = new_statements
    update_assume_role_policy(iam_client, service_role_name, current_policy_document)
    return external_id


@tracer.capture_method(capture_response=False)
def delete_iam_trust(service_role_name: str, product_role_arn: str) -> None:
    iam_client = boto3.client('iam')
    current_policy_document = get_trust_policy(iam_client, service_role_name)

    new_statements = clean_statements(current_policy_document.get('Statement', []), product_role_arn)

    # replace statements with new_statements
    current_policy_document['Statement'] = new_statements
    update_assume_role_policy(iam_client, service_role_name, current_policy_document)
