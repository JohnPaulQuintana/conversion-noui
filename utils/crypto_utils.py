import os
from typing import Dict, Any
from utils.logger import Logger
from utils.google_client import get_gspread_client
from utils.env_loader import get_env
from datetime import datetime

gc = get_gspread_client()
sh = gc.open_by_key(get_env("SHEET_URL"))


def get_or_create_tab(sh, tab_name, fieldnames):
    """Return worksheet, create if missing with header row."""
    try:
        ws = sh.worksheet(tab_name)
    except Exception:
        ws = sh.add_worksheet(title=tab_name, rows="1000", cols="30")
        ws.append_row(fieldnames)
        return ws

    headers = ws.row_values(1)
    if not headers:
        ws.append_row(fieldnames)
    return ws


def fetch_today_bonasa_row(sh, today):
    """
    Fetch today's row from BONASA tab.
    Returns a dict: {"date": str, "bdt_purchase_rate": float, "effective_conversion_rate": float}
    or None if no match is found.
    """
    try:
        ws = sh.worksheet("BONASA")
    except Exception:
        return None  # Sheet not found

    col_a = ws.col_values(1)  # Column A (dates)
    for idx, val in enumerate(col_a, start=1):  # Google Sheets rows are 1-based
        try:
            # Convert cell to datetime.date (Sheet date format may be "d/m/YYYY")
            cell_date = datetime.strptime(val.strip(), "%d/%m/%Y").date()
            if cell_date == today:
                row = ws.row_values(idx)
                return {
                    "date": val.strip(),
                    "bdt_purchase_rate": float(row[1]) if len(row) > 1 and row[1] else None,
                    "effective_conversion_rate": float(row[2]) if len(row) > 2 and row[2] else None,
                }
        except ValueError:
            continue  # Skip invalid rows

    return None


def calculate_diff_and_save(
    binance_usdtusd: Any,
    xe_data: Any,
    current_usd_value: Dict[str, Any],
    bo_brand: str,
    crypto_data: Dict[str, Any],
    converted_currency_value: Any,  # dict or dict_items
    logger: Logger,
    p2p_service,
    localtime
):
    """
    Calculate % differences and save results directly into Google Sheets.
    Two tabs:
      - LocalDiff (BTC/ETH with BO vs Converted values)
      - P2P_USDT (top 5 Binance P2P ads)
    """
    if not isinstance(converted_currency_value, dict):
        converted_currency_value = dict(converted_currency_value)

    # 🔍 Fetch BONASA row once (so we don't call the API repeatedly)
    # ✅ Fix localtime parsing: handle both datetime object and string with time
    if hasattr(localtime, "date"):  
        today_date = localtime.date()
    else:
        # Automatically handle strings like "2025-09-17" or "2025-09-17 15:42:57"
        try:
            today_date = datetime.fromisoformat(localtime).date()
        except ValueError:
            today_date = datetime.strptime(localtime.split()[0], "%Y-%m-%d").date()

    bonasa_row = fetch_today_bonasa_row(sh, today_date)
    effective_conversion_rate = (
        bonasa_row["effective_conversion_rate"]
        if bonasa_row and bonasa_row["effective_conversion_rate"]
        else 0
    )


    diff_results_local = []
    diff_results_usdt = []
    print(f"USDT/USD price: {binance_usdtusd}")
    for crypto, bo_list in crypto_data.items():
        crypto_upper = crypto.strip().upper()

        # Handle USDT separately (P2P ads)
        if crypto_upper == "USDT" and crypto_upper not in converted_currency_value:
            logger.success(f"Processing {crypto_upper}")
            for bo_entry in bo_list:
                reused_currency = bo_entry["currency"].strip().upper()
                reused_bo_value = bo_entry["marketPrice"]
                xe_rate = xe_data.get("rates", {}).get(reused_currency, 1)
                print("ITS BEING CALLED.....")
                p2p_usdt_result = p2p_service.fetch_top5_completed_order_rates(
                    reused_currency
                )

                # logger.error(f"Currency: {reused_currency}, Effective Conversion Rate: {effective_conversion_rate}")

                if reused_currency == "BDT":
                    if effective_conversion_rate > 0:
                        binance_rate_used = effective_conversion_rate
                        logger.info(f"Using BONASA Effective Conversion Rate: {binance_rate_used}")
                    else:
                        # 👇 Force to 0 instead of using Binance fallback
                        binance_rate_used = 0
                        logger.warn("BDT has no effective conversion rate → Setting Binance Rate and Exchange Rate to 0")
                else:
                    binance_rate_used = p2p_usdt_result.get("binance_rate", 0)

                # calculate (Binance_rate - BO) / BO * 100
                if binance_rate_used > 0:
                    exchange_rate = ((binance_rate_used - reused_bo_value) / reused_bo_value) * 100
                else:
                    exchange_rate = 0

                # logger.info(f"({p2p_usdt_result.get("binance_rate", 0)}) - {reused_bo_value} / {reused_bo_value} * 100")
                # exchange_rate = (
                #     (p2p_usdt_result.get("binance_rate", 0) - reused_bo_value) 
                #     / reused_bo_value
                # ) * 100

                top_ads = p2p_usdt_result.get("top_ads", [])
                row_usdt = {
                    "Date": localtime,
                    "Brand": bo_brand,
                    "Crypto": crypto_upper,
                    "Currency": reused_currency,
                    "USD": float(binance_usdtusd.get("data", {}).get("USDT", {}).get("price", 1.0)),
                    "XE RATE": round(xe_rate, 2) if xe_rate else None,
                    "BO Market Price": reused_bo_value,
                    "Binance Rate": round(binance_rate_used, 2),
                    # "Binance Rate": round(p2p_usdt_result.get("binance_rate", 0), 2),
                    "Exchange Rate": round(exchange_rate, 2),
                    # "Exchange Rate": round(exchange_rate if exchange_rate <= 3 else 3, 2) if exchange_rate > 0 else round(exchange_rate, 2),
                    "Exchange Rate Sign": "Positive" if exchange_rate >= 0 else "Negative",
                }

                for i in range(5):
                    if i < len(top_ads):
                        row_usdt[f"Top{i+1}_Nick"] = top_ads[i].get("nick", "")
                        row_usdt[f"Top{i+1}_Orders"] = top_ads[i].get("orders", "")
                        row_usdt[f"Top{i+1}_Price"] = top_ads[i].get("price", "")
                    else:
                        row_usdt[f"Top{i+1}_Nick"] = ""
                        row_usdt[f"Top{i+1}_Orders"] = ""
                        row_usdt[f"Top{i+1}_Price"] = ""

                diff_results_usdt.append(row_usdt)
                logger.success(f"→ {row_usdt}")
            continue

        # Handle BTC/ETH (and others in converted_currency_value)
        usd_price = None
        if crypto_upper in current_usd_value:
            try:
                usd_price = float(current_usd_value[crypto_upper].get("price", 0))
            except Exception:
                usd_price = None

        converted_currencies = converted_currency_value.get(crypto_upper, {})
        for bo_entry in bo_list:
            currency = bo_entry["currency"].strip().upper()
            bo_value = bo_entry["marketPrice"]

            if currency not in converted_currencies:
                logger.warn(
                    f"Skipping {crypto_upper}-{currency}, not in converted_currency_value"
                )
                continue

            converted_value = converted_currencies[currency]
            try:
                diff_percent = (
                    (converted_value - bo_value)
                    / ((converted_value + bo_value) / 2)
                    * 100
                )
                diff_sign = "Positive" if diff_percent >= 0 else "Negative"
            except ZeroDivisionError:
                diff_percent = None
                diff_sign = "N/A"

            row = {
                "Date": localtime,
                "Brand": bo_brand,
                "Crypto": crypto_upper,
                "Currency": currency,
                "USD Price": round(usd_price, 2),
                "BO Market Price": round(bo_value, 2),
                "Binance Rate": round(converted_value, 2),
                "Exchange Rate": round(diff_percent if diff_percent <= 3 else 3, 2) if diff_percent > 0 else round(diff_percent, 2),
                "Exchange Rate Sign": diff_sign,
            }
            diff_results_local.append(row)
            logger.success(f"→ {row}")

    # ✅ Save LocalDiff (BTC/ETH)
    if diff_results_local:
        fieldnames_local = [
            "Date",
            "Brand",
            "Crypto",
            "Currency",
            "USD Price",
            "BO Market Price",
            "Binance Rate",
            "Exchange Rate",
            "Exchange Rate Sign",
        ]
        ws_local = get_or_create_tab(sh, "BTC_AND_ETH_CONVERSION", fieldnames_local)
        rows = [list(row.values()) for row in diff_results_local]
        ws_local.append_rows(rows, value_input_option="USER_ENTERED")
        logger.success("→ Differences appended to Google Sheet: LocalDiff")

    # ✅ Save USDT (P2P)
    if diff_results_usdt:
        fieldnames_usdt = ["Date", "Brand", "Crypto", "Currency", "BO Market Price", "Binance Rate", "Exchange Rate", "Exchange Rate Sign"]
        for i in range(1, 6):
            fieldnames_usdt += [f"Top{i}_Nick", f"Top{i}_Orders", f"Top{i}_Price"]

        ws_usdt = get_or_create_tab(sh, "USDT_CONVERSION", fieldnames_usdt)
        rows = [list(row.values()) for row in diff_results_usdt]
        ws_usdt.append_rows(rows, value_input_option="USER_ENTERED")
        logger.success("→ USDT P2P rates appended to Google Sheet: P2P_USDT")
