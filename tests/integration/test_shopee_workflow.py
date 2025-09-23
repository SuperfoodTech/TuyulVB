import pytest
import runpy
from unittest.mock import patch, MagicMock


@pytest.mark.integration
# Simulate running all accounts then exiting
@patch('builtins.input', side_effect=['1', 'exit_option'])
@patch('services.base.service_factory.ServiceFactory.get_shopee_scraper')
@patch('services.base.service_factory.ServiceFactory.get_sheets_client')
def test_shopee_workflow_runs_without_errors(mock_sheets_client, mock_shopee_scraper, monkeypatch):
    """
    An integration test to ensure the Shopee validation workflow runs end-to-end
    without crashing. This test mocks the external services.
    """
    # Prevent the script from actually trying to exit
    monkeypatch.setattr("builtins.exit", lambda: None)

    # Mock the return value for reading the worksheet
    mock_sheets_client.return_value.read_worksheet_as_dataframe.return_value = MagicMock()

    try:
        runpy.run_path(
            'monday-automation/shopee-scrapper/shopee-store-validation.py', run_name='__main__')
    except Exception as e:
        pytest.fail(f"Shopee workflow failed with an exception: {e}")
