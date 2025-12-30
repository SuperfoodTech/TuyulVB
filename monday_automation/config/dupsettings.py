# ... (your existing settings)

# --- Monday.com Configuration ---
MONDAY_BOARD_ID_SSOT = 2075483964
MONDAY_BOARD_ID_VBO = 5016848191

MONDAY_TARGET_GROUP_ID_SSOT = "group_mkvxp4cr"
MONDAY_TARGET_GROUP_NAME_SSOT = "Merchant - Outlet - VB (Database)"

MONDAY_TARGET_GROUP_ID_VBO = "group_mkx04smk"
MONDAY_TARGET_GROUP_NAME_VBO = "VBO Naming"

DUPLICATE_CHECKS_SSOT = [
    {"source": "Name", "target": "Outlet Duplicate"},
    {"source": "F - Go & S Long Name", "target": "F - Long Duplicate"},
    {"source": "W - Go & S Long Name", "target": "W - Long Duplicate"},
    {"source": "L - Go & S Long Name", "target": "L - Long Duplicate"},
    {"source": "DE - Go & S Long Name", "target": "DE - Long Duplicate"},
    {"source": "F - S Short Name", "target": "F - Short Duplicate"},
    {"source": "W - S Short Name", "target": "W - Short Duplicate"},
    {"source": "L - S Short Name", "target": "L - Short Duplicate"},
    {"source": "DE - S Short Name", "target": "DE - Short Duplicate"},
    {"source": "F - S SID", "target": "F - S SID Duplicate"},
    {"source": "W - S SID", "target": "W - S SID Duplicate"},
    {"source": "L - S SID", "target": "L - S SID Duplicate"},
    {"source": "DE - S SID", "target": "DE - S SID Duplicate"},
    {"source": "F - Gr Name", "target": "F - Gr Duplicate"},
    {"source": "W - Gr Name", "target": "W - Gr Duplicate"},
    {"source": "L - Gr Name", "target": "L - Gr Duplicate"},
    {"source": "DE - Gr Name", "target": "DE - Gr Duplicate"},
    {"source": "F - Gr SID", "target": "F - Gr SID Duplicate"},
    {"source": "W - Gr SID", "target": "W - Gr SID Duplicate"},
    {"source": "L - Gr SID", "target": "L - Gr SID Duplicate"},
    {"source": "DE - Gr SID", "target": "DE - Gr SID Duplicate"},
]

DUPLICATE_CHECKS_VBO = [
    {"source": "Go & S Long Name", "target": "Go & S Long Duplicate"},
    {"source": "S Short Name", "target": "S Short Duplicate"},
    {"source": "Gr Name", "target": "Gr Duplicate"},
]

MONDAY_BOARD_ID_ORDERID = 5016253339
MONDAY_TARGET_GROUP_ID_ORDERID = ["group_mkwyswjg", "group_mky71bdz", "group_mky7kgxk"]
MONDAY_TARGET_GROUP_NAME_ORDERID = "Manual Disbursement"
DUPLICATE_CHECKS_ORDERID = [{"source": "Order ID", "target": "Duplicate"}]
