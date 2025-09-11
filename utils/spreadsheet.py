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

def read_and_calculate_bonasa_sheet_tab(logger, localtime, lookahead_days: int = 6) -> Dict[str, Any]:
    try:
        logger.info(f"→ Opening worksheet: {tab}...")
        worksheet = shs.worksheet(tab)
        
        rows = worksheet.get_all_values()
        print(rows)
        if len(rows) <= 1:
            logger.warning("⚠️ No data (only header row found)")
            return {}

        logger.success("→ Successfully read sheet values")

        # Compatible with Windows + matches sheet format (5/9/2025 not 05/09/2025)
        today_str = f"{localtime.day}/{localtime.month}/{localtime.year}"
        logger.info(f"→ Looking for today: {today_str}")

        # Find the index of today
        date_list = [row[0].strip() for row in rows[1:] if row and row[0].strip()]
        if today_str not in date_list:
            logger.warning("⚠️ Today's date not found in sheet")
            return {}

        today_idx = date_list.index(today_str) + 1  # +1 because of header
        today_row = rows[today_idx]

        results: Dict[str, Any] = {
            "today": None,
            "consecutive": []
        }

        # Process today's row
        if len(today_row) >= 2 and today_row[1].strip():
            try:
                original = float(today_row[1])
                effective = round(original * 1.01, 2)
                results["today"] = {
                    "Date": today_row[0],
                    "Purchase Rate": original,
                    "Effective Conversion Rate": effective,
                }
            except ValueError:
                results["today"] = {
                    "Date": today_row[0],
                    "Purchase Rate": today_row[1],
                    "Effective Conversion Rate": None,
                }

        # Process consecutive rows (future days)
        consecutive_rows = rows[today_idx + 1 : today_idx + 1 + lookahead_days]
        for row in consecutive_rows:
            if len(row) >= 2:
                purchase_rate = row[1].strip()
                if purchase_rate:
                    try:
                        original = float(purchase_rate)
                        effective = round(original * 1.01, 2)
                        results["consecutive"].append(
                            {
                                "Date": row[0],
                                "Purchase Rate": original,
                                "Effective Conversion Rate": effective,
                            }
                        )
                    except ValueError:
                        results["consecutive"].append(
                            {
                                "Date": row[0],
                                "Purchase Rate": purchase_rate,
                                "Effective Conversion Rate": None,
                            }
                        )
                else:
                    # Keep track of empty future rows
                    results["consecutive"].append(
                        {
                            "Date": row[0],
                            "Purchase Rate": None,
                            "Effective Conversion Rate": None,
                        }
                    )

        return results

    except Exception as e:
        logger.error(f"❌ Error reading sheet: {e}")
        return {}



def save_effective_conversion(logger: Logger, results: Dict[str, Any]) -> None:
    try:
        logger.info("→ Opening automation worksheet...")

        # Prepare today's row
        today_data = results.get("today", {})
        if not today_data:
            logger.warning("⚠️ No today data found, skipping save")
            return

        today_date = today_data.get("Date", datetime.now().strftime("%d/%m/%Y"))
        purchase_rate = today_data.get("Purchase Rate", "")
        effective_rate = today_data.get("Effective Conversion Rate", "")

        new_row = [today_date, purchase_rate, effective_rate]

        # Try to get worksheet, else create it dynamically
        try:
            worksheet = sh.worksheet("BONASA")
        except Exception:
            worksheet = sh.add_worksheet(title="BONASA", rows="2", cols="3")
            worksheet.append_row(["DATE", "PURCHASE RATE", "EFFECTIVE CONVERSION RATE"])
            logger.info("→ Created worksheet BONASA")

        logger.success("→ Automation worksheet ready")

        # Get all values to check existing dates
        rows = worksheet.get_all_values()
        existing_dates = [r[0] for r in rows[1:]]  # skip header

        if today_date in existing_dates:
            # Update existing row
            row_index = existing_dates.index(today_date) + 2  # +2 because of header row + 1-based index
            worksheet.update(f"A{row_index}:C{row_index}", [new_row])
            logger.success(f"→ Updated row for {today_date}")
        else:
            # Append new row
            worksheet.append_row(new_row, value_input_option="USER_ENTERED")
            logger.success(f"→ Added new row for {today_date}")

    except Exception as e:
        logger.error(f"❌ Error saving to sheet: {e}")
