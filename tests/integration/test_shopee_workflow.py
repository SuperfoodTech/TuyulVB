import pytest
import runpy
from unittest.mock import patch, MagicMock


@pytest.mark.integration
@patch('services.base.service_factory.ServiceFactory.get_sheets_client')
@patch('services.base.service_factory.ServiceFactory.get_shopee_scraper')
def test_shopee_workflow_runs_without_errors(mock_get_shopee_scraper, mock_get_sheets_client, monkeypatch):
    """
    An integration test to ensure the Shopee validation workflow runs end-to-end
    without crashing. This test mocks the external services.
    """
    # Mock the input to select "run all"
    monkeypatch.setattr('builtins.input', lambda _: '1')
    # Prevent the script from calling sys.exit()
    monkeypatch.setattr("builtins.exit", lambda: None)

    # Configure the mocks returned by the factory
    mock_sheets_client = MagicMock()
    mock_shopee_scraper = MagicMock()
    mock_get_sheets_client.return_value = mock_sheets_client
    mock_get_shopee_scraper.return_value = mock_shopee_scraper

    try:
        # Execute the script's main function
        runpy.run_path(
            'monday-automation/shopee-scrapper/shopee-store-validation.py', run_name='__main__')
    except Exception as e:
        pytest.fail(f"Shopee workflow failed with an exception: {e}")

    # Assert that the key methods were called
    mock_sheets_client.read_worksheet_as_dataframe.assert_called()
    mock_shopee_scraper.login.assert_called()
    mock_shopee_scraper.collect_data.assert_called()
