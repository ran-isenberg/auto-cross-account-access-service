import json
from typing import Annotated, Literal
from urllib.parse import urlparse

import boto3
import requests
from aws_lambda_env_modeler import get_environment_variables, init_environment_variables
from aws_lambda_powertools.logging import Logger
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.utilities import parameters
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_requests_auth.aws_auth import AWSRequestsAuth
from pydantic import BaseModel, Field

logger: Logger = Logger()
tracer: Tracer = Tracer()


class Observability(BaseModel):
    POWERTOOLS_SERVICE_NAME: Annotated[str, Field(min_length=1)]
    LOG_LEVEL: Literal['DEBUG', 'INFO', 'ERROR', 'CRITICAL', 'WARNING', 'EXCEPTION']


class EnvVars(Observability):
    API_URL: Annotated[str, Field(min_length=1)]
    PRODUCT_VERSION: Annotated[str, Field(min_length=1)]
    CONSUMER_NAME: Annotated[str, Field(min_length=1)]


def get_ssm_parameters(consumer_name: str, product_version: str) -> tuple:
    ssm_dict = json.loads(parameters.get_parameter(f'/orders/{consumer_name}/{product_version}'))
    logger.info(f'got ssm parameters: {ssm_dict}')
    return ssm_dict['mediatorRoleArn'], ssm_dict['ordersAssumeRoleArn'], ssm_dict['ordersExternalId']


def assume_role(role_arn: str, session_name: str):
    client = boto3.client('sts')
    response = client.assume_role(RoleArn=role_arn, RoleSessionName=session_name)
    credentials = response['Credentials']
    return credentials['AccessKeyId'], credentials['SecretAccessKey'], credentials['SessionToken']


def get_auth_with_assume_role_with_creds(
    role_arn: str, session_name: str, access_key: str, secret_key: str, session_token: str, external_id: str, host: str
) -> AWSRequestsAuth:
    client = boto3.client('sts', aws_access_key_id=access_key, aws_secret_access_key=secret_key, aws_session_token=session_token)
    response = client.assume_role(
        RoleArn=role_arn,
        RoleSessionName=session_name,
        ExternalId=external_id,
    )

    temp_credentials = response['Credentials']
    auth = AWSRequestsAuth(
        aws_access_key=temp_credentials['AccessKeyId'],
        aws_secret_access_key=temp_credentials['SecretAccessKey'],
        aws_token=temp_credentials['SessionToken'],
        aws_host=host,
        aws_region='us-east-1',
        aws_service='execute-api',
    )
    return auth


@init_environment_variables(model=EnvVars)
@logger.inject_lambda_context()
@tracer.capture_lambda_handler(capture_response=False)
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    logger.info('processing event')
    env_vars: EnvVars = get_environment_variables(model=EnvVars)
    mediator_role, assume_role_arn, external_id = get_ssm_parameters(env_vars.CONSUMER_NAME, env_vars.PRODUCT_VERSION)
    full_url = f'{env_vars.API_URL}api/orders'
    host = urlparse(url=full_url).hostname
    body = {'order': 'my_order'}

    # Post a JSON body without IAM token and assert we get 403 Forbidden
    logger.info(f'calling {full_url}')
    response = requests.post(full_url, json=body)
    assert response.status_code == 403, f'Expected status code 403, but got {response.status_code}'
    logger.info('first request received expected 403 Forbidden status.')

    logger.info('assuming mediator role')
    access_key_1, secret_key_1, session_token_1 = assume_role(mediator_role, 'mysession')

    logger.info('Assuming the service role and retrying the request')
    auth = get_auth_with_assume_role_with_creds(assume_role_arn, 'secondSession', access_key_1, secret_key_1, session_token_1, external_id, host)

    response = requests.post(full_url, timeout=10, auth=auth, json=body)
    assert response.status_code == 200, f'Expected status code 200, but got {response.status_code}'
    logger.info('got 200 OK, created order')
    return {'statusCode': 200}
