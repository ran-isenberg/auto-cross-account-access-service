import json

import boto3
import pytest


@pytest.mark.skip('Skipping demo test')
def test_invoke_demo_lambda(demo_lambda_name: str):
    client = boto3.client('lambda')
    response = client.invoke(
        FunctionName=demo_lambda_name,
        InvocationType='RequestResponse',
        LogType='Tail',
    )
    assert response['StatusCode'] == 200, f'Expected status code 200, but got {response["StatusCode"]}'
    payload = json.loads(response['Payload'].read().decode('utf-8'))
    print('Lambda response payload:', payload)
    assert payload['statusCode'] == 200, f'Expected status code in payload to be 200, but got {payload["statusCode"]}'
