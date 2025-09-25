from typing import List, Dict, Any
from utils.logger import Logger
from utils.google_client import get_gspread_client
from utils.env_loader import get_env
from datetime import datetime

gc = get_gspread_client()
sh = gc.open_by_key(get_env("SHEET_URL"))
shs = gc.open_by_key("1BV2gS30b0r28qnTJAXvRYz_6DiCa9KBsdI5izro5hCY")  # Souce Sheet
tab = get_env("BONASA_TAB", "BONASA")
result_tab = get_env("EFFECTIVE_CONVERSION_RATE_TAB", "EFFECTIVE CONVERSION RATE")

from datetime import datetime
from typing import Dict, Any, List

def read_and_calculate_bonasa_sheet_tab(logger: Logger) -> List[Dict[str, Any]]:
    """Read all rows from the source sheet and calculate effective rates."""
    try:
        logger.info(f"→ Opening worksheet: {tab}...")
        worksheet = shs.worksheet(tab)
        rows = worksheet.get_all_values()

        if len(rows) <= 1:
            logger.warning("⚠️ No data (only header row found)")
            return []

        logger.success("→ Successfully read sheet values")

        results: List[Dict[str, Any]] = []
        for row in rows[1:]:  # skip header
            if len(row) < 2:
                continue
            date_str = row[0].strip()
            purchase_rate = row[1].strip()
            effective_rate = None
            if purchase_rate:
                try:
                    original = float(purchase_rate)
                    effective_rate = round(original * 1.01, 2)
                except ValueError:
                    effective_rate = None

            results.append({
                "Date": date_str,
                "Purchase Rate": purchase_rate or None,
                "Effective Conversion Rate": effective_rate
            })

        return results

    except Exception as e:
        logger.error(f"❌ Error reading sheet: {e}")
        return []



def save_effective_conversion(logger: Logger, all_rows: List[Dict[str, Any]]) -> None:
    """Ensure all dates are saved in the target sheet up to today."""
    try:
        # Try to get worksheet, else create it
        try:
            worksheet = sh.worksheet("BONASA")
        except Exception:
            worksheet = sh.add_worksheet(title="BONASA", rows="2", cols="3")
            worksheet.append_row(["DATE", "PURCHASE RATE", "EFFECTIVE CONVERSION RATE"])
            logger.info(f"→ Created worksheet BONASA")

        existing_rows = worksheet.get_all_values()
        existing_dates = [r[0] for r in existing_rows[1:]]  # skip header

        today = datetime.now()

        for row in all_rows:
            row_date = datetime.strptime(row["Date"], "%d/%m/%Y")
            if row_date > today:
                # skip future dates
                continue

            new_row = [row["Date"], row["Purchase Rate"], row["Effective Conversion Rate"]]

            if row["Date"] in existing_dates:
                row_index = existing_dates.index(row["Date"]) + 2  # header + 1-based index
                worksheet.update(f"A{row_index}:C{row_index}", [new_row])
                logger.success(f"→ Updated row for {row['Date']}")
            else:
                worksheet.append_row(new_row, value_input_option="USER_ENTERED")
                logger.success(f"→ Added new row for {row['Date']}")

        logger.success("→ All dates processed and saved successfully")

    except Exception as e:
        logger.error(f"❌ Error saving to sheet: {e}")
