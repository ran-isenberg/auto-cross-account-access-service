import json
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError

from catalog_backend.handlers.utils.observability import logger


def create_statement_and_external_id(product_role_arn: str) -> tuple[dict, str]:
    external_id = str(uuid4())
    # ideally, you should save external id per consumer_name
    statement = {
        'Effect': 'Allow',
        'Principal': {'AWS': product_role_arn},
        'Action': 'sts:AssumeRole',
        'Condition': {'StringEquals': {'sts:ExternalId': external_id}},
    }
    return statement, external_id


def update_assume_role_policy(iam_client: boto3.client, trust_role_name: str, current_policy_document: dict):
    # Update the trust policy
    logger.info('updating trust policy')
    try:
        iam_client.update_assume_role_policy(RoleName=trust_role_name, PolicyDocument=json.dumps(current_policy_document))
    except ClientError as exc:
        error_str = 'failed to update trust policy'
        logger.exception(error_str)
        raise exc


def clean_statements(statements: list, arn_to_remove: str) -> list[dict]:
    new_statements = []
    for statement_item in statements:
        principal_arn = statement_item.get('Principal', {}).get('AWS')
        # if found old product arn statement, dont append it to new_statements, delete it
        if principal_arn == arn_to_remove:
            # we dont append the statement, thus "deleting" it
            logger.info('deleting old arn statement')
            continue
        else:
            new_statements.append(statement_item)
    return new_statements


def get_trust_policy(iam_client: boto3.client, trust_role_name: str) -> dict:
    logger.info('fetching current trust policy')
    try:
        response = iam_client.get_role(RoleName=trust_role_name)
        return response['Role']['AssumeRolePolicyDocument']
    except (ClientError, KeyError) as exc:
        logger.exception('failed to fetch trust policy')
        raise exc
