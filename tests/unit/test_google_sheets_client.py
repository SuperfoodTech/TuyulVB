import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import gspread
from services.google_sheets.client import GoogleSheetsClient
from services.base.exceptions import APIError, ConfigurationError


@patch('services.google_sheets.client.authorize_service_account')
def test_google_sheets_client_initialization_success(mock_authorize):
    """Test that GoogleSheetsClient initializes successfully with a mock client."""
    mock_client = MagicMock()
    mock_authorize.return_value = mock_client

    client = GoogleSheetsClient(creds_file="dummy_creds.json")

    assert client.client is not None
    assert client.client == mock_client
    mock_authorize.assert_called_once_with("dummy_creds.json")


@patch('services.google_sheets.client.authorize_service_account', side_effect=FileNotFoundError)
def test_google_sheets_client_initialization_file_not_found(mock_authorize):
    """Test that a ConfigurationError is raised if the credentials file is not found."""
    with pytest.raises(ConfigurationError, match="Google Sheets credentials file not found"):
        GoogleSheetsClient(creds_file="non_existent.json")


@patch('services.google_sheets.client.authorize_service_account')
def test_read_worksheet_as_dataframe_success(mock_authorize):
    """Test reading a worksheet as a pandas DataFrame successfully."""
    mock_worksheet = MagicMock()
    mock_worksheet.get_all_values.return_value = [
        ['col1', 'col2'],
        ['val1', 'val2']
    ]

    mock_spreadsheet = MagicMock()
    mock_spreadsheet.worksheet.return_value = mock_worksheet

    mock_client = MagicMock()
    mock_client.open.return_value = mock_spreadsheet
    mock_authorize.return_value = mock_client

    client = GoogleSheetsClient()
    df = client.read_worksheet_as_dataframe('test_sheet', 'test_ws')

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ['col1', 'col2']
    assert df.iloc[0]['col1'] == 'val1'
    mock_client.open.assert_called_once_with('test_sheet')
    mock_spreadsheet.worksheet.assert_called_once_with('test_ws')


@patch('services.google_sheets.client.authorize_service_account')
def test_read_worksheet_not_found(mock_authorize):
    """Test that an APIError is raised when a worksheet is not found."""
    mock_spreadsheet = MagicMock()
    mock_spreadsheet.worksheet.side_effect = gspread.exceptions.WorksheetNotFound

    mock_client = MagicMock()
    mock_client.open.return_value = mock_spreadsheet
    mock_authorize.return_value = mock_client

    client = GoogleSheetsClient()
    with pytest.raises(APIError, match="Worksheet 'test_ws' not found in spreadsheet 'test_sheet'."):
        client.read_worksheet_as_dataframe('test_sheet', 'test_ws')


@patch('services.google_sheets.client.authorize_service_account')
def test_write_dataframe_to_worksheet_api_error(mock_authorize):
    """Test that an APIError is raised during a gspread API error."""
    mock_spreadsheet = MagicMock()
    # Simulate gspread's APIError which can be raised with a mock response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'error': {'code': 500, 'message': 'Test API Error'}}
    mock_spreadsheet.worksheet.side_effect = gspread.exceptions.APIError(
        mock_response)

    mock_client = MagicMock()
    mock_client.open.return_value = mock_spreadsheet
    mock_authorize.return_value = mock_client

    client = GoogleSheetsClient()
    df = pd.DataFrame({'col1': [1], 'col2': [2]})

    with pytest.raises(APIError, match="An API error occurred while writing to worksheet"):
        client.write_dataframe_to_worksheet(df, 'test_sheet', 'test_ws')
