# --- Monday.com Configuration ---
# Board containing the source data for validation
SOURCE_BOARD_ID = 2075483964
MONDAY_SOURCE_GROUP_ID = "group_mkvxp4cr"
MONDAY_SOURCE_GROUP_NAME = "Merchant - Outlet - VB (Database)"

# Board where the validation results will be reported
DESTINATION_BOARD_ID = 5000872897

MONDAY_SID_COLUMN_MAP = {
    "F1": "text_mkvwxk2b",
    "F2": "text_mkvwxk2b",
    "F2S": "text_mkvwxk2b",
    "W1": "text_mkvwfxq0",
    "L1": "text_mkvwag6j",
    "L2": "text_mkvwag6j",
    "DE1": "text_mkvwejkw",
    "DE1S": "text_mkvwejkw",
    "FM4": "text_mkvwxk2b",
}

DESTINATION_GROUP_ID = "group_mks93rx3"  # Group to report missing outlets
