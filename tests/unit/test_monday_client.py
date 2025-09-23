import pytest
import requests
from unittest.mock import patch, MagicMock
from services.monday.client import MondayClient
from services.base.exceptions import APIError, AuthenticationError, ConfigurationError


@pytest.fixture
def monday_client():
    with patch.dict('os.environ', {'MONDAY_API_KEY': 'test_key'}):
        client = MondayClient()
    return client


def test_monday_client_initialization_success():
    with patch.dict('os.environ', {'MONDAY_API_KEY': 'test_key'}):
        client = MondayClient()
        assert client.api_key == 'test_key'


def test_monday_client_initialization_no_key():
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ConfigurationError, match='MONDAY_API_KEY not provided'):
            MondayClient()


@patch('requests.post')
def test_run_query_success(mock_post, monday_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'data': 'success'}
    mock_post.return_value = mock_response

    response = monday_client.run_query('query {}')
    assert response == {'data': 'success'}
    mock_post.assert_called_once()


@patch('requests.post')
def test_run_query_graphql_error(mock_post, monday_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'errors': [{'message': 'Something went wrong'}]}
    mock_post.return_value = mock_response

    response = monday_client.run_query('query {}')
    assert 'errors' in response


@patch('requests.post')
def test_run_query_authentication_error(mock_post, monday_client):
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_post.return_value = mock_response
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=mock_response)

    with pytest.raises(AuthenticationError, match="Unauthorized"):
        monday_client.run_query('query {}')


@patch('requests.post')
@patch('time.sleep', return_value=None)
def test_run_query_rate_limit_retry_success(mock_sleep, mock_post, monday_client):
    # First call: rate limit error
    rate_limit_response = MagicMock()
    rate_limit_response.status_code = 429
    rate_limit_response.json.return_value = {
        'extensions': {'retry_in_seconds': 1}}
    rate_limit_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=rate_limit_response)

    # Second call: success
    success_response = MagicMock()
    success_response.status_code = 200
    success_response.json.return_value = {'data': 'success'}

    mock_post.side_effect = [rate_limit_response, success_response]

    response = monday_client.run_query('query {}')
    assert response == {'data': 'success'}
    assert mock_post.call_count == 2
    mock_sleep.assert_called_once()


@patch('requests.post')
@patch('time.sleep', return_value=None)
def test_run_query_rate_limit_max_retries_fails(mock_sleep, mock_post, monday_client):
    rate_limit_response = MagicMock()
    rate_limit_response.status_code = 429
    rate_limit_response.json.return_value = {
        'extensions': {'retry_in_seconds': 1}}
    rate_limit_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=rate_limit_response)

    mock_post.return_value = rate_limit_response

    with pytest.raises(APIError, match="Max retries reached"):
        monday_client.run_query('query {}', max_retries=3)

    assert mock_post.call_count == 3
    assert mock_sleep.call_count == 2
