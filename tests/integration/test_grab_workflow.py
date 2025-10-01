from unittest.mock import patch, MagicMock
import runpy
import pytest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..')))


@pytest.mark.integration
@patch('services.base.service_factory.ServiceFactory.get_sheets_client')
@patch('services.base.service_factory.ServiceFactory.get_grab_scraper')
def test_grab_workflow_runs_without_errors(mock_get_grab_scraper, mock_get_sheets_client, monkeypatch):
    """
    An integration test to ensure the Grab validation workflow runs end-to-end
    without crashing. This test mocks the external services.
    """
    # Mock the input to select "run all"
    monkeypatch.setattr('builtins.input', lambda _: '1')
    # Prevent the script from calling sys.exit()
    monkeypatch.setattr("builtins.exit", lambda: None)

    # Configure the mocks returned by the factory
    mock_sheets_client = MagicMock()
    mock_grab_scraper = MagicMock()
    mock_get_sheets_client.return_value = mock_sheets_client
    mock_get_grab_scraper.return_value = mock_grab_scraper

    try:
        # Execute the script's main function
        runpy.run_path(
            'monday-automation/grab-scrapper/grab-store-validation.py', run_name='__main__')
    except Exception as e:
        pytest.fail(f"Grab workflow failed with an exception: {e}")

    # Assert that the key methods were called
    mock_sheets_client.read_worksheet_as_dataframe.assert_called()
    mock_grab_scraper.login.assert_called()
    mock_grab_scraper.collect_data.assert_called()
