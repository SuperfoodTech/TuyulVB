import gspread
import pandas as pd


class GSheet:
    def __init__(self, credentials_path, spreadsheet_id):
        self.gc = gspread.service_account(filename=credentials_path)
        self.sh = self.gc.open_by_key(spreadsheet_id)

    def get_worksheet_as_dataframe(self, worksheet_name):
        worksheet = self.sh.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)

    def update_worksheet_from_dataframe(self, worksheet_name, dataframe):
        worksheet = self.sh.worksheet(worksheet_name)
        worksheet.update([dataframe.columns.values.tolist()
                          ] + dataframe.values.tolist())
