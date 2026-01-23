import argparse
import getpass
import json
import os
from datetime import datetime
from typing import Dict, List

import pandas as pd
import requests
import time
import random
from common import monday_utils


DEFAULT_MERCHANTS = ["6-C7EHLGKXLLLKCE"]

# Default mapping inferred from Monday (fallback). Keys are brand keywords -> Gr SID value
DEFAULT_BRAND_MAPPING = {
    "Foodnesia": "text_mky9b8z9",
    "WonderFood": "text_mky974s9",
    "Lokarasa": "text_mky9pxvr",
}


def prompt_auth() -> Dict[str, str]:
    print("Enter authentication values for Grab requests.")
    x_hydra_jwt = getpass.getpass("x-hydra-jwt (hidden): ")
    cookies = getpass.getpass("Cookies header (full cookie string, hidden): ")
    return {"x-hydra-jwt": x_hydra_jwt, "cookies": cookies}


def build_headers(auth: Dict[str, str]) -> Dict[str, str]:
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "id",
        "origin": "https://food.grab.com",
        "referer": "https://food.grab.com/",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        ),
        "x-country-code": "ID",
        "x-gfc-country": "ID",
    }
    if auth.get("x-hydra-jwt"):
        headers["x-hydra-jwt"] = auth["x-hydra-jwt"]
    if auth.get("cookies"):
        headers["Cookie"] = auth["cookies"]
    return headers


def fetch_merchant(
    session: requests.Session,
    merchant_id: str,
    headers: Dict[str, str],
    max_retries: int = 5,
) -> dict:
    """
    Fetch merchant JSON with retries, exponential backoff and jitter on 429/connection errors.
    """
    url = f"https://portal.grab.com/foodweb/guest/v2/merchants/{merchant_id}?latlng=-7.28573,112.65145"

    backoff = 1.0
    for attempt in range(1, max_retries + 1):
        try:
            resp = session.get(url, headers=headers, timeout=30)

            if resp.status_code == 429:
                # Respect Retry-After header if provided
                retry_after = resp.headers.get("Retry-After")
                try:
                    wait = (
                        float(retry_after)
                        if retry_after is not None
                        else backoff + random.uniform(0, backoff)
                    )
                except Exception:
                    wait = backoff + random.uniform(0, backoff)
                time.sleep(wait)
                backoff = min(backoff * 2, 60)
                continue

            resp.raise_for_status()
            return resp.json()

        except requests.exceptions.RequestException as e:
            if attempt == max_retries:
                raise
            wait = backoff + random.uniform(0, backoff)
            time.sleep(wait)
            backoff = min(backoff * 2, 60)
            continue


def detect_brand(merchant: dict) -> str:
    name = merchant.get("chainName") or merchant.get("name") or ""
    for keyword in DEFAULT_BRAND_MAPPING.keys():
        if keyword.lower() in name.lower():
            return keyword
    # fallback: try branchName
    branch = merchant.get("branchName", "")
    for keyword in DEFAULT_BRAND_MAPPING.keys():
        if keyword.lower() in branch.lower():
            return keyword
    return ""


def parse_menu(merchant_json: dict, brand_mapping: Dict[str, str]) -> List[dict]:
    merchant = merchant_json.get("merchant", {})
    menu = merchant.get("menu", {})
    categories = menu.get("categories", [])
    results = []

    brand = detect_brand(merchant)
    gr_sid_value = brand_mapping.get(brand, "")

    for cat in categories:
        cat_name = cat.get("name")
        items = cat.get("items", [])
        # some categories include elementCards which can contain item under 'item'
        for it in items:
            row = build_row(merchant, brand, gr_sid_value, cat_name, it)
            results.append(row)

        # handle elementCards if present
        for card in cat.get("elementCards", []):
            item = card.get("item")
            if item:
                row = build_row(merchant, brand, gr_sid_value, cat_name, item)
                results.append(row)

    return results


def build_row(
    merchant: dict, brand: str, gr_sid_value: str, category_name: str, item: dict
) -> dict:
    # Helpers to safely extract nested numeric prices
    def safe_amount(dct, key_path: List[str]):
        cur = dct
        for k in key_path:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(k)
            if cur is None:
                return None
        return cur

    price_minor = (
        safe_amount(item, ["priceV2", "amountInMinor"])
        or safe_amount(item, ["priceInMinorUnit"])
        or None
    )
    discounted_minor = (
        safe_amount(item, ["discountedPriceV2", "amountInMinor"])
        or safe_amount(item, ["discountedPriceInMin"])
        or None
    )

    # Normalise by dividing by 100 per instructions
    def norm(v):
        try:
            return float(v) / 100.0 if v is not None else None
        except Exception:
            return None

    fake_price_gr = norm(price_minor)
    gr_price = norm(discounted_minor)

    row = {
        "Fullname": merchant.get("name", ""),
        "Shortname": "",
        "Comb Item": "",
        "SID": "",
        "Gr - SID": merchant.get("ID", ""),
        "Outlet": "",
        "Klikit Brand Name": "",
        "Price level": brand,
        "Category": category_name,
        "Item": item.get("name", ""),
        "Description": item.get("description", ""),
        "Slash Price": "",
        "Flash Sale": "",
        "Modifier Group Code": "",
        "COGS Menu 🔥": "",
        "Category 🔥": "",
        "Item 🔥": "",
        "Description 🔥": "",
        "Max %🔥 Go": "",
        "Max Rp 🔥 Go": "",
        "Fake Price Go": "",
        "Markup % 🔥 Go": "",
        "Slash Price Rp 🔥 Go": "",
        "Slash Price % Go": "",
        "Go Price": "",
        "Max %🔥 Gr": "",
        "Max Rp 🔥 Gr": "",
        "Fake Price Gr": fake_price_gr,
        "Markup % 🔥 Gr": "",
        "Slash Price Rp 🔥 Gr": "",
        "Slash Price % Gr": "",
        "Gr Price": gr_price,
        "Max % 🔥 S": "",
        "Max Rp 🔥 S": "",
        "Fake Price S": "",
        "Markup % 🔥 S": "",
        "Slash Price Rp 🔥 S": "",
        "Slash Price % S": "",
        "S Price": "",
    }
    return row


def write_excel(rows: List[dict], output_file: str):
    df = pd.DataFrame(rows)

    # Ensure the Price level ordering
    sort_order = ["Foodnesia", "WonderFood", "Lokarasa"]
    df["Price level"] = pd.Categorical(
        df["Price level"], categories=sort_order, ordered=True
    )

    df.sort_values(
        by=["Price level", "Fullname", "SID", "Category", "Item"], inplace=True
    )

    # Write to excel and format currency for price columns
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
        workbook = writer.book
        worksheet = writer.sheets["Sheet1"]

        # Attempt to format the two price columns as IDR currency
        try:
            from openpyxl.styles import numbers

            # find column letters
            for col_name in ["Fake Price Gr", "Gr Price"]:
                if col_name in df.columns:
                    col_idx = df.columns.get_loc(col_name) + 1
                    # openpyxl is 1-based and Excel header present -> start row 2
                    for row_idx in range(2, 2 + len(df)):
                        cell = worksheet.cell(row=row_idx, column=col_idx)
                        if isinstance(cell.value, (int, float)):
                            # Indonesian rupiah style
                            cell.number_format = "Rp#,##0.00"
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Extract Grab merchant menu to Excel")
    parser.add_argument("--output", "-o", default="menu.xlsx", help="Output Excel file")
    parser.add_argument(
        "--merchant-ids",
        "-m",
        help="Comma separated merchant ids to fetch (default example merchant)",
    )
    parser.add_argument(
        "--brand-mapping",
        "-b",
        help=(
            "Optional JSON string or path to JSON file mapping brand->Gr-SID. "
            'Example: \'{"Foodnesia": "text_mky9b8z9"}\''
        ),
    )

    args = parser.parse_args()

    if args.merchant_ids:
        merchant_ids = [s.strip() for s in args.merchant_ids.split(",") if s.strip()]
    else:
        merchant_ids = None

    # load mapping
    brand_mapping = DEFAULT_BRAND_MAPPING.copy()
    if args.brand_mapping:
        try:
            # try to parse as JSON first
            bm = json.loads(args.brand_mapping)
            if isinstance(bm, dict):
                brand_mapping.update(bm)
        except Exception:
            # try to open file
            try:
                with open(args.brand_mapping, "r", encoding="utf-8") as f:
                    bm = json.load(f)
                    if isinstance(bm, dict):
                        brand_mapping.update(bm)
            except Exception:
                print("Warning: could not parse brand mapping; using defaults")

    auth = prompt_auth()
    headers = build_headers(auth)

    # Use a single session for connection pooling and to help with rate limits
    session = requests.Session()
    session.headers.update(headers)

    # Prepare timestamped output filename inside modules/grab/
    out_dir = os.path.dirname(__file__)
    os.makedirs(out_dir, exist_ok=True)

    # Use provided output as prefix if given, otherwise use 'menu'
    if args.output:
        base = os.path.splitext(os.path.basename(args.output))[0]
    else:
        base = "menu"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(out_dir, f"{base}_{timestamp}.xlsx")

    all_rows = []

    # If merchant_ids provided via CLI, use them. Otherwise fetch SIDs from Monday board/group.
    if merchant_ids:
        mids_to_fetch = merchant_ids
    else:
        BOARD_ID = 5025182611
        GROUP_ID = "group_mkys1dmf"
        col_ids = ["text_mky9b8z9", "text_mky974s9", "text_mky9pxvr"]

        print(f"Fetching Gr SIDs from Monday board {BOARD_ID}, group {GROUP_ID}...")
        items = monday_utils.get_all_items_from_group(BOARD_ID, GROUP_ID, col_ids)

        mids_to_fetch = []
        seen = set()
        mapping = {
            "Foodnesia": "text_mky9b8z9",
            "WonderFood": "text_mky974s9",
            "Lokarasa": "text_mky9pxvr",
        }

        for item in items:
            for brand, col in mapping.items():
                val = monday_utils.get_col_value(item, col).strip()
                if not val:
                    continue
                # handle multiple SIDs separated by commas or whitespace
                for part in [
                    p.strip() for p in val.replace(";", ",").split(",") if p.strip()
                ]:
                    if part not in seen:
                        seen.add(part)
                        mids_to_fetch.append(part)

    for mid in mids_to_fetch:
        print(f"Fetching merchant {mid}...")
        try:
            mj = fetch_merchant(session, mid, headers)
        except Exception as e:
            print(f"Failed to fetch {mid}: {e}")
            # Sleep a bit before continuing to avoid hot loops
            time.sleep(random.uniform(1.0, 3.0))
            continue

        rows = parse_menu(mj, brand_mapping)
        all_rows.extend(rows)

        # polite throttle between requests
        time.sleep(random.uniform(0.5, 1.5))

    if not all_rows:
        print("No rows parsed. Exiting.")
        return

    write_excel(all_rows, output_file)
    print(f"Wrote {len(all_rows)} rows to {output_file}")


if __name__ == "__main__":
    main()
