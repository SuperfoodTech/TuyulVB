"""Google Sheets auth helper.
"""
from typing import Optional
import os
import gspread
from google.oauth2.service_account import Credentials


def authorize_service_account(creds_file: Optional[str] = None) -> gspread.Client:
    creds_file = creds_file or os.getenv('GOOGLE_CREDS_FILE')
    if not creds_file:
        raise RuntimeError('GOOGLE_CREDS_FILE not set')
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_file(creds_file, scopes=scopes)
    return gspread.authorize(creds)
