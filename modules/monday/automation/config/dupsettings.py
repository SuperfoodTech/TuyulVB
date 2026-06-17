# --- Monday.com Configuration ---

# === SSOT CONFIGURATION ===
MONDAY_BOARD_ID_SSOT = 2075483964
MONDAY_TARGET_GROUP_ID_SSOT = "group_mkvxp4cr"
MONDAY_TARGET_GROUP_NAME_SSOT = (
    "Merchant - Outlet - VB (Database)"  # Name kept for reference/logging
)

DUPLICATE_CHECKS_SSOT = [
    # Name
    {
        "source": "Name",
        "target": "Outlet Duplicate",
        "target_id": "color_mktzwy5j",
    },
    # Long Name
    {
        "source": "F - Go & S Long Name",
        "source_id": "text_mkvwh85b",
        "target": "F - Long Duplicate",
        "target_id": "color_mkvw1w76",
    },
    {
        "source": "W - Go & S Long Name",
        "source_id": "text_mkvwb097",
        "target": "W - Long Duplicate",
        "target_id": "color_mkvw1c65",
    },
    {
        "source": "L - Go & S Long Name",
        "source_id": "text_mkvw3wpf",
        "target": "L - Long Duplicate",
        "target_id": "color_mkvwk48d",
    },
    {
        "source": "DE - Go & S Long Name",
        "source_id": "text_mkvwdkte",
        "target": "DE - Long Duplicate",
        "target_id": "color_mkvwwjz7",
    },
    # Short Name
    {
        "source": "F - S Short Name",
        "source_id": "text_mkvwebs8",
        "target": "F - Short Duplicate",
        "target_id": "color_mkvw9c6e",
    },
    {
        "source": "W - S Short Name",
        "source_id": "text_mkvwwe3d",
        "target": "W - Short Duplicate",
        "target_id": "color_mkvweqgx",
    },
    {
        "source": "L - S Short Name",
        "source_id": "text_mkvw9kd0",
        "target": "L - Short Duplicate",
        "target_id": "color_mkvwgkqz",
    },
    {
        "source": "DE - S Short Name",
        "source_id": "text_mkvw6xae",
        "target": "DE - Short Duplicate",
        "target_id": "color_mkvwdnq",
    },
    # SID
    {
        "source": "F - S SID",
        "source_id": "text_mktz8s96",
        "target": "F - S SID Duplicate",
        "target_id": "color_mkvwjrk",
    },
    {
        "source": "W - S SID",
        "source_id": "text_mkvwqq8c",
        "target": "W - S SID Duplicate",
        "target_id": "color_mkvw917h",
    },
    {
        "source": "L - S SID",
        "source_id": "text_mkvw90wc",
        "target": "L - S SID Duplicate",
        "target_id": "color_mkvwmmm3",
    },
    {
        "source": "DE - S SID",
        "source_id": "text_mkvwzjaa",
        "target": "DE - S SID Duplicate",
        "target_id": "color_mkvwrpvp",
    },
    # Grab
    {
        "source": "F - Gr Name",
        "source_id": "text_mkvw7015",
        "target": "F - Gr Duplicate",
        "target_id": "color_mkvwz82g",
    },
    {
        "source": "W - Gr Name",
        "source_id": "text_mkvwcpne",
        "target": "F - Gr Duplicate",
        "target_id": "color_mkvwkqdp",
    },
    {
        "source": "L - Gr Name",
        "source_id": "text_mkvwhzr3",
        "target": "F - Gr Duplicate",
        "target_id": "color_mkvw5qaq",
    },
    {
        "source": "DE - Gr Name",
        "source_id": "text_mkvwzs6m",
        "target": "F - Gr Duplicate",
        "target_id": "color_mkvwk0nj",
    },
    # SID
    {
        "source": "F - Gr SID",
        "source_id": "text_mkvwxk2b",
        "target": "F - Gr SID Duplicate",
        "target_id": "color_mkvw6cc8",
    },
    {
        "source": "W - Gr SID",
        "source_id": "text_mkvwfxq0",
        "target": "W - Gr SID Duplicate",
        "target_id": "color_mkvwknmt",
    },
    {
        "source": "L - Gr SID",
        "source_id": "text_mkvwag6j",
        "target": "L - Gr SID Duplicate",
        "target_id": "color_mkvwqc9v",
    },
    {
        "source": "DE - Gr SID",
        "source_id": "text_mkvwejkw",
        "target": "DE - Gr SID Duplicate",
        "target_id": "color_mkvwtq76",
    },
]

# === VBO CONFIGURATION ===
MONDAY_BOARD_ID_VBO = 5016848191
MONDAY_TARGET_GROUP_ID_VBO = "group_mkx04smk"
MONDAY_TARGET_GROUP_NAME_VBO = "VBO Naming"

DUPLICATE_CHECKS_VBO = [
    {"source": "Go & S Long Name", "target": "Go & S Long Duplicate"},
    {"source": "S Short Name", "target": "S Short Duplicate"},
    {"source": "Gr Name", "target": "Gr Duplicate"},
]

# === ORDER ID CONFIGURATION ===
MONDAY_BOARD_ID_ORDERID = 5016253339
MONDAY_TARGET_GROUP_ID_ORDERID = ["group_mkwyswjg", "group_mky71bdz", "group_mky7kgxk"]
MONDAY_TARGET_GROUP_NAME_ORDERID = "Manual Disbursement"
DUPLICATE_CHECKS_ORDERID = [{"source": "Order ID", "target": "Duplicate"}]
