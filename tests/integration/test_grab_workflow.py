from unittest.mock import patch, MagicMock
import runpy
import pytest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..')))


@pytest.mark.integration
# Simulate running all accounts then exiting
@patch('builtins.input', side_effect=['1', 'exit_option'])
@patch('services.base.service_factory.ServiceFactory.get_grab_scraper')
@patch('services.base.service_factory.ServiceFactory.get_sheets_client')
def test_grab_workflow_runs_without_errors(mock_sheets_client, mock_grab_scraper, monkeypatch):
    """
    An integration test to ensure the Grab validation workflow runs end-to-end
    without crashing. This test mocks the external services.
    """
    # Prevent the script from actually trying to exit
    monkeypatch.setattr("builtins.exit", lambda: None)

    # Mock the return value for reading the worksheet
    mock_sheets_client.return_value.read_worksheet_as_dataframe.return_value = MagicMock()

    try:
        # Execute the script using runpy
        runpy.run_path(
            'monday-automation/grab-scrapper/grab-store-validation.py', run_name='__main__')
    except Exception as e:
        pytest.fail(f"Grab workflow failed with an exception: {e}")
