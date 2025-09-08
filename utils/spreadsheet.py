from typing import List, Dict, Any
from utils.logger import Logger
from utils.google_client import get_gspread_client
from utils.env_loader import get_env
from datetime import datetime

gc = get_gspread_client()
sh = gc.open_by_key(get_env("SHEET_URL"))
tab = get_env("BONASA_TAB", "BONASA")
result_tab = get_env("EFFECTIVE_CONVERSION_RATE_TAB", "EFFECTIVE CONVERSION RATE")

def read_and_calculate_bonasa_sheet_tab(logger: Logger, localtime) -> Dict[str, Any]:
    try:
        logger.info("→ Opening worksheet...")
        worksheet = sh.worksheet(tab)

        rows = worksheet.get_all_values()

        if len(rows) <= 1:
            logger.warning("⚠️ No data (only header row found)")
            return []

        logger.success("→ Successfully read sheet values")

        results: List[Dict[str, Any]] = []

        # Skip header (row 1), read row 2+
        for row in rows[1:]:
            if len(row) >= 2:
                key, value = row[0].strip(), row[1].strip()
                if key and value:
                    try:
                        original = float(value)
                        effective = round(original * 1.01, 2)
                        results.append(
                            {
                                "Date": key,
                                "BDT Purchase Rate": original,
                                "Effective Conversion Rate": effective,
                            }
                        )
                    except ValueError:
                        results.append(
                            {
                                "Date": key,
                                "BDT Purchase Rate": value,
                                "Effective Conversion Rate": None,
                            }
                        )

        return results

    except Exception as e:
        logger.error(f"❌ Error reading sheet: {e}")
        return []

def save_effective_conversion(logger: Logger, results: List[Dict[str, Any]]) -> None:
    try:
        logger.info("→ Opening automation worksheet...")

        # Get or create automation tab
        try:
            worksheet = sh.worksheet("EFFECTIVE CONVERSION RATE")
        except Exception:
            worksheet = sh.add_worksheet(title="BONASA_AUTOMATION", rows="1000", cols="2")
            worksheet.append_row(["Automation Date", "Effective Conversion Rate"])

        logger.success("→ Automation worksheet ready")

        # Prepare new rows
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_rows = [[now, row["Effective Conversion Rate"]] for row in results]

        # Append rows (no overwrite)
        worksheet.append_rows(new_rows, value_input_option="USER_ENTERED")

        logger.success(f"→ Saved {len(new_rows)} rows to EFFECTIVE CONVERSION RATE")

    except Exception as e:
        logger.error(f"❌ Error saving to sheet: {e}")