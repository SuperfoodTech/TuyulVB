"""Lightweight Google Sheets client wrapper."""
import logging
from typing import Optional
import pandas as pd
import gspread
from gspread_formatting import *
from .auth import authorize_service_account
from ..base.exceptions import APIError, ConfigurationError

log = logging.getLogger(__name__)


class GoogleSheetsClient:
    def __init__(self, creds_file: Optional[str] = None):
        try:
            self.client = authorize_service_account(creds_file)
        except FileNotFoundError:
            raise ConfigurationError(
                f"Google Sheets credentials file not found at {creds_file or 'default path'}")
        except Exception as e:
            raise APIError(f"Failed to authorize Google Sheets client: {e}")

    def open_sheet(self, name: str) -> gspread.Spreadsheet:
        return self.client.open(name)

    def get_worksheet(self, sheet_name: str, worksheet_name: str) -> gspread.Worksheet:
        sh = self.open_sheet(sheet_name)
        return sh.worksheet(worksheet_name)

    def read_worksheet_as_dataframe(self, sheet_name: str, worksheet_name: str) -> Optional[pd.DataFrame]:
        try:
            worksheet = self.get_worksheet(sheet_name, worksheet_name)
            all_values = worksheet.get_all_values()
            if len(all_values) < 2:
                log.warning(
                    f"Worksheet '{worksheet_name}' has insufficient data.")
                return None
            header = all_values[0]
            data = all_values[1:]
            return pd.DataFrame(data, columns=header)
        except gspread.exceptions.WorksheetNotFound:
            log.error(
                f"Worksheet '{worksheet_name}' not found in spreadsheet '{sheet_name}'.")
            raise APIError(
                f"Worksheet '{worksheet_name}' not found in spreadsheet '{sheet_name}'.")
        except gspread.exceptions.APIError as e:
            log.error(
                f"An API error occurred while reading from worksheet '{worksheet_name}': {e}")
            raise APIError(
                f"An API error occurred while reading from worksheet '{worksheet_name}': {e}")

    def write_dataframe_to_worksheet(self, df: pd.DataFrame, sheet_name: str, worksheet_name: str, apply_formatting: bool = True):
        try:
            spreadsheet = self.open_sheet(sheet_name)
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
                worksheet.clear()
            except gspread.exceptions.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(
                    title=worksheet_name, rows="1", cols="1")

            df_to_write = df.fillna('').astype(str)
            worksheet.update(
                [df_to_write.columns.values.tolist()] + df_to_write.values.tolist())

            if apply_formatting and not df_to_write.empty:
                self._apply_conditional_formatting(worksheet, df_to_write)

            return True
        except gspread.exceptions.APIError as e:
            log.error(
                f"An API error occurred while writing to worksheet '{worksheet_name}': {e}")
            raise APIError(
                f"An API error occurred while writing to worksheet '{worksheet_name}': {e}")
        except Exception as e:
            log.error(
                f"An unexpected error occurred while writing to sheet: {e}")
            raise APIError(f"Unexpected error writing to sheet: {e}")

    def _apply_conditional_formatting(self, worksheet: gspread.Worksheet, df: pd.DataFrame):
        green_format = CellFormat(backgroundColor=Color(0.85, 0.96, 0.85))
        yellow_format = CellFormat(backgroundColor=Color(1, 0.95, 0.8))
        red_format = CellFormat(backgroundColor=Color(0.96, 0.85, 0.85))
        grey_format = CellFormat(backgroundColor=Color(0.9, 0.9, 0.9))

        headers = df.columns.values.tolist()
        try:
            name_result_col_letter = gspread.utils.rowcol_to_a1(
                1, headers.index('Name Result') + 1)[0]
            address_result_col_letter = gspread.utils.rowcol_to_a1(
                1, headers.index('Address Result') + 1)[0]

            name_result_range = f'{name_result_col_letter}2:{name_result_col_letter}{len(df) + 1}'
            address_result_range = f'{address_result_col_letter}2:{address_result_col_letter}{len(df) + 1}'

            rules = get_conditional_format_rules(worksheet)
            rules.clear()

            ranges_to_format = [GridRange.from_a1_range(name_result_range, worksheet),
                                GridRange.from_a1_range(address_result_range, worksheet)]

            rules.append(ConditionalFormatRule(
                ranges=ranges_to_format,
                booleanRule=BooleanRule(condition=BooleanCondition(
                    'TEXT_CONTAINS', ['True']), format=green_format)
            ))
            rules.append(ConditionalFormatRule(
                ranges=ranges_to_format,
                booleanRule=BooleanRule(condition=BooleanCondition(
                    'TEXT_CONTAINS', ['Warning']), format=yellow_format)
            ))
            rules.append(ConditionalFormatRule(
                ranges=ranges_to_format,
                booleanRule=BooleanRule(condition=BooleanCondition(
                    'TEXT_CONTAINS', ['False']), format=red_format)
            ))
            rules.append(ConditionalFormatRule(
                ranges=ranges_to_format,
                booleanRule=BooleanRule(condition=BooleanCondition(
                    'TEXT_CONTAINS', ['N/A']), format=grey_format)
            ))

            rules.save()
        except (ValueError, gspread.exceptions.APIError) as e:
            print(f"Could not apply conditional formatting. Error: {e}")
