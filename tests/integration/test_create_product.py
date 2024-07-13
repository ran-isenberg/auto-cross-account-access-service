from copy import deepcopy
from datetime import datetime, timezone

import boto3

from tests.integration.utils import (
    RESOURCE_PROPERTIES,
    assert_crhelper_response,
    call_handle_product_event,
    check_db_entry_exists,
    create_product_body,
    create_sqs_records,
    is_role_arn_in_trust_relationship,
    mock_crhelper,
)
from tests.utils import generate_random_string


def test_create_product_success(mocker, table_name, portfolio_id):
    product_stack_id = f'arn:aws:cloudformation:us-east-1:123456789012:stack/SC-123456789012-pp-yuqxzldfdagkq/{generate_random_string(12)}'
    event = create_sqs_records(create_product_body('Create', product_stack_id, RESOURCE_PROPERTIES))
    crhelper_mock = mock_crhelper(mocker)
    call_handle_product_event(event)
    assert_crhelper_response(success=True, crhelper_mock=crhelper_mock)

    # check that product is in dynamoDB after create event
    dynamodb_table = boto3.resource('dynamodb').Table(table_name)
    response = dynamodb_table.get_item(
        Key={
            'portfolio_id': portfolio_id,
            'product_stack_id': product_stack_id,
        }
    )
    _assert_db_item(response['Item'], portfolio_id, product_stack_id)
    # delete entry
    response = dynamodb_table.delete_item(Key={'portfolio_id': portfolio_id, 'product_stack_id': product_stack_id})


def _assert_db_item(item: dict, portfolio_id: str, product_stack_id: str):
    assert item['version'] == RESOURCE_PROPERTIES['product_version']
    assert item['account_id'] == RESOURCE_PROPERTIES['account_id']
    assert item['consumer_name'] == RESOURCE_PROPERTIES['consumer_name']
    assert item['region'] == RESOURCE_PROPERTIES['region']
    assert item['portfolio_id'] == portfolio_id
    assert item['product_stack_id'] == product_stack_id
    assert item['created_at'] is not None
    now = int(datetime.now(timezone.utc).timestamp())
    assert now - int(item['created_at']) <= 60  # assume item was created in last minute, check that utc time calc is correct


def test_create_product_failure_empty_resource_props_body_input(mocker):
    event = create_sqs_records(create_product_body('Create', 'aaaa', {}))
    crhelper_mock = mock_crhelper(mocker)
    call_handle_product_event(event)
    assert_crhelper_response(success=False, crhelper_mock=crhelper_mock)


def test_create_cross_account_access_product_success(
    mocker, table_name: str, portfolio_id: str, test_role_arn: str, service_role_arn: str, service_role_name: str
):
    product_stack_id = f'arn:aws:cloudformation:us-east-1:123456789012:stack/SC-123456789012-pp-yuqxzldfdagkq/{generate_random_string(12)}'
    cfn_props = deepcopy(RESOURCE_PROPERTIES)
    cfn_props['trust_role_arn'] = test_role_arn  # add trust role arn to the payload, we will add its ARNs to the service role trust relationship
    event = create_sqs_records(create_product_body('Create', product_stack_id, cfn_props))
    crhelper_mock = mock_crhelper(mocker)
    call_handle_product_event(event)

    # assert crhelper returns correct items
    assert_crhelper_response(success=True, crhelper_mock=crhelper_mock, expected_service_role_arn=service_role_arn)

    # check that product is in dynamoDB after create event
    dynamodb_table = boto3.resource('dynamodb').Table(table_name)
    response = dynamodb_table.get_item(
        Key={
            'portfolio_id': portfolio_id,
            'product_stack_id': product_stack_id,
        }
    )
    _assert_db_item(response['Item'], portfolio_id, product_stack_id)

    # assert that the service role trust relationship has the test role ARN
    assert is_role_arn_in_trust_relationship(service_role_name=service_role_name, product_role_arn=test_role_arn)

    # delete flow
    event = create_sqs_records(create_product_body('Delete', product_stack_id, cfn_props))
    call_handle_product_event(event)
    assert_crhelper_response(success=True, crhelper_mock=crhelper_mock, call_count=4)

    # check that product is deleted from dynamoDB after delete event
    assert not check_db_entry_exists(table_name, portfolio_id, product_stack_id)
    # assert that the service role trust relationship does not have the test role ARN
    assert not is_role_arn_in_trust_relationship(service_role_name=service_role_name, product_role_arn=test_role_arn)
