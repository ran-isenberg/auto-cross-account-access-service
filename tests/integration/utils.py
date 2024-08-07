import json
from typing import Any, Optional
from unittest.mock import ANY, MagicMock

import boto3

from tests.utils import generate_context


def call_handle_product_event(event: dict[str, Any]) -> dict[str, Any]:
    from catalog_backend.handlers.product_callback_handler import handle_product_event

    return handle_product_event(event, generate_context())


def is_role_arn_in_trust_relationship(product_role_arn: str, service_role_name: str) -> bool:
    """
    Check if a given role ARN appears in the trust relationship document of another role.

    :param role_arn: The ARN of the role to check.
    :param trust_role_name: The name of the role whose trust relationship document will be checked.
    :return: True if the role ARN appears in the trust relationship document, False otherwise.
    """
    client = boto3.client('iam')

    # Get the trust relationship document of the trust_role_name
    response = client.get_role(RoleName=service_role_name)
    trust_relationship = response['Role']['AssumeRolePolicyDocument']

    # Convert the trust relationship document to a JSON string for easier processing
    trust_relationship_str = json.dumps(trust_relationship)

    # Check if the role ARN appears in the trust relationship document
    return product_role_arn in trust_relationship_str


def mock_crhelper(mocker) -> MagicMock:
    # crhelper.utils.HTTPSConnection.getresponse: mock the response for the crhelper.utils.HTTPSConnection.request
    crhelper_getresponse_mock = mocker.patch('crhelper.utils.HTTPSConnection.getresponse')
    # crhelper expects reason field in response
    crhelper_getresponse_mock.return_value.reason = 'ok'

    # crhelper.utils.HTTPSConnection.request: mock the class used by crhelper to send responses to the custom resource
    crhelper_send_response_mock = mocker.patch('crhelper.utils.HTTPSConnection.request')
    return crhelper_send_response_mock


def assert_crhelper_response(success: bool, crhelper_mock: MagicMock, expected_service_role_arn: str = '', call_count: int = 2):
    assert crhelper_mock.call_count == call_count
    actual_call_args = crhelper_mock.call_args[1]
    body = json.loads(actual_call_args['body'])
    if success:
        assert body['Status'] == 'SUCCESS'
    else:
        assert body['Status'] == 'FAILED'
        assert body['Reason'] == ANY
    if expected_service_role_arn:
        assert body['Data']['assume_role_arn'] == expected_service_role_arn
        assert body['Data']['external_id']


def check_db_entry_exists(table_name: str, portfolio_id: str, product_stack_id: str) -> bool:
    dynamodb_table = boto3.resource('dynamodb').Table(table_name)
    response = dynamodb_table.get_item(
        Key={
            'portfolio_id': portfolio_id,
            'product_stack_id': product_stack_id,
        }
    )
    return response.get('Item', None)


def create_product_body(request_type: str, stack_id: str, resource_properties: dict, old_resource_properties: Optional[dict] = None) -> str:
    body = {
        'RequestType': request_type,
        'ServiceToken': 'arn:aws:sns:us-east-1:123456789012:ranisenberg-custom-PlatformCatalog-dev-GovernanceCatalogTopic',
        'ResponseURL': 'https://cloudformation-custom-resource-response-useast1.s3.amazonaws.com/arn%3Aaws%3Acloudformation%3Aus-east-1%3A123456789012%3Astack/SC-123456789012-pp-yuqxzldfdagkq/1dbb0a20-14e8-11ef-a95c-0eaa9ec0a8b1%7CPlatformGovernanceCustomResource%7Ccc5ad960-e179-4f71-8fdc-3513cdc604a8?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20240518T072804Z&X-Amz-SignedHeaders=host&X-Amz-Expires=7200&X-Amz-Credential=Afdsfdsfs0518%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=3f4fgdgdfgfdg',
        'StackId': stack_id,
        'RequestId': 'cc5ad960-e179-4f71-8fdc-3513cdc604a8',
        'PhysicalResourceId': 'unique-physical-resource-id',
        'LogicalResourceId': 'PlatformGovernanceCustomResource',
        'ResourceType': 'Custom::PlatformEngGovernanceEnabler',
        'ResourceProperties': resource_properties,
    }
    if old_resource_properties:
        body['OldResourceProperties'] = old_resource_properties
    return json.dumps(body)


def create_sqs_records(body: str) -> dict:
    return {
        'Records': [
            {
                'messageId': '428bfb11-fda9-4299-9f16-b215d0deb1a3',
                'receiptHandle': 'AQEB2mXyP3uOkgsIMNWwbVjc6f+4bJDVPG2T+iROmjKnjcMRPHzpYaPbCgPmIH/Tt2lX2EcXD7BHHnBG9O/N2etG9FwxY0gt7tLn6kK0LcnOyKn43PeUlFn5HPUn6bY2VE3TycfPQjm7xK8FHANs6+0l61YuL/EtW8SOp5tayfTfo0TmAsBZhgWUIFEAzec7Q4QePsfgerNzRSifow6qvNy3M0Txn98VlUyih7Ettd/j00X7tTlAT1f7EFwDB2jsQOTAOGTmFRJsAivBnvHxtzZIAiwSIIluzqlK3gna88iLpkuCM/dWFdIKMaU+E65y5ZfGLzNRq8JEwPRoj4pPcxtv6jiPHJ3+XMp9KhGcxvYU4Huxr4KGujKghCf8S9lJb/YXJm1xHpSWZdJAQSwjBk3nYpZ+K/JC7hYG/HQH8h1RbTKVOo2U7eIuAWRvx1dv2esYNiqfjrsTojBJec9MVx31fg==',
                'body': body,
                'attributes': {
                    'ApproximateReceiveCount': '3',
                    'SentTimestamp': '1716017284863',
                    'SenderId': 'AIDAIT2UOQQY3AUEKVGXU',
                    'ApproximateFirstReceiveTimestamp': '1716017284872',
                },
                'messageAttributes': {},
                'md5OfBody': '6552016cbc63089b262c550fbb2b63b5',
                'eventSource': 'aws:sqs',
                'eventSourceARN': 'arn:aws:sqs:us-east-1:123456789012:ranisenberg-custom-PlatformCatalog-dev-GovernanceCatalogSQS',
                'awsRegion': 'us-east-1',
            }
        ]
    }


RESOURCE_PROPERTIES = {
    'ServiceToken': 'arn:aws:sns:us-east-1:123456789012:ranisenberg-custom-PlatformCatalog-dev-GovernanceCatalogTopic',
    'product_version': '1.0.0',
    'account_id': '123456789012',
    'consumer_name': 'Ran isenberg',
    'region': 'us-east-1',
    'product_name': 'CI/CD IAM Role Product',
}

NEW_RESOURCE_PROPERTIES = {
    'ServiceToken': 'arn:aws:sns:us-east-1:123456789012:ranisenberg-custom-PlatformCatalog-dev-GovernanceCatalogTopic',
    'product_version': '2.0.0',
    'account_id': '123456789012',
    'consumer_name': 'Ran isenberg',
    'region': 'us-east-1',
    'product_name': 'CI/CD IAM Role Product v2',
}
