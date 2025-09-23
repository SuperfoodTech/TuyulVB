import pandas as pd
from services.utils.logging import setup_logging
import logging

log = logging.getLogger(__name__)


def restructure_data_from_google_sheet(df, column_mapping):
    tasks = []
    log.info("🛠️ Restructuring data...")

    all_required_cols = set()
    for mapping in column_mapping:
        all_required_cols.update([
            mapping["outlet_name"],
            mapping["ofd_name_col"],
            mapping["id_col"]
        ])

    if not all_required_cols.issubset(df.columns):
        missing_cols = all_required_cols - set(df.columns)
        log.error(
            f"The following required columns are missing from your sheet: {', '.join(missing_cols)}")
        return []

    for index, row in df.iterrows():
        for mapping in column_mapping:
            ofd_name = row.get(mapping["ofd_name_col"])

            if pd.notna(ofd_name) and str(ofd_name).strip() != "":
                store_id_raw = row.get(mapping["id_col"])

                tasks.append({
                    "outlet_name": str(row.get(mapping["outlet_name"], "")).strip(),
                    "ofd_name": str(ofd_name).strip(),
                    "store_id": str(store_id_raw).strip() if pd.notna(store_id_raw) else "",
                    "source_portal": mapping["source_portal"],
                })
    return tasks
