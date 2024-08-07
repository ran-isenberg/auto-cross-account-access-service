import os

import pytest

from cdk.demo.constants import (
    METRICS_DIMENSION_VALUE,
    METRICS_NAMESPACE,
    PORTFOLIO_ID_OUTPUT,
    POWER_TOOLS_LOG_LEVEL,
    POWERTOOLS_SERVICE_NAME,
    SERVICE_NAME,
    TABLE_NAME_OUTPUT,
)
from tests.utils import get_stack_output


@pytest.fixture(scope='module', autouse=True)
def init():
    os.environ[POWERTOOLS_SERVICE_NAME] = SERVICE_NAME
    os.environ['POWERTOOLS_METRICS_NAMESPACE'] = METRICS_NAMESPACE
    os.environ[POWER_TOOLS_LOG_LEVEL] = 'DEBUG'
    os.environ['METRICS_DIMENSION_KEY'] = METRICS_DIMENSION_VALUE
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'  # used for appconfig mocked boto calls
    os.environ['TABLE_NAME'] = get_stack_output(TABLE_NAME_OUTPUT)
    os.environ['PORTFOLIO_ID'] = get_stack_output(PORTFOLIO_ID_OUTPUT)
    os.environ['SERVICE_ROLE_ARN'] = get_stack_output('ServiceRoleArn')
    os.environ['SERVICE_ROLE_NAME'] = get_stack_output('ServiceRoleName')
    os.environ['TEST_ROLE_ARN'] = get_stack_output('TestRoleArn')
    os.environ['TEST_ROLE_NAME'] = get_stack_output('TestRoleName')
    os.environ['API_URL'] = get_stack_output('TrustApiUrl')
    os.environ['DEMO_LAMBDA'] = get_stack_output('DemoLambda')


@pytest.fixture(scope='module', autouse=False)
def demo_lambda_name():
    return os.environ['DEMO_LAMBDA']


@pytest.fixture(scope='module', autouse=False)
def api_url():
    return os.environ['API_URL']


@pytest.fixture(scope='module', autouse=False)
def table_name():
    return os.environ['TABLE_NAME']


@pytest.fixture(scope='module', autouse=False)
def portfolio_id():
    return os.environ['PORTFOLIO_ID']


@pytest.fixture(scope='module', autouse=False)
def test_role_arn():
    return os.environ['TEST_ROLE_ARN']


@pytest.fixture(scope='module', autouse=False)
def service_role_arn():
    return os.environ['SERVICE_ROLE_ARN']


@pytest.fixture(scope='module', autouse=True)
def service_role_name():
    return os.environ['SERVICE_ROLE_NAME']
