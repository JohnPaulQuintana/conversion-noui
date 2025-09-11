import os
from typing import Dict, Any
from utils.logger import Logger
from utils.google_client import get_gspread_client
from utils.env_loader import get_env

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
                p2p_usdt_result = p2p_service.fetch_top5_completed_order_rates(
                    reused_currency
                )

                # calculate (Binance_rate - BO) / BO * 100
                logger.info(f"({p2p_usdt_result.get("binance_rate", 0)}) - {reused_bo_value} / {reused_bo_value} * 100")
                exchange_rate = (
                    (p2p_usdt_result.get("binance_rate", 0) - reused_bo_value) 
                    / reused_bo_value
                ) * 100

                top_ads = p2p_usdt_result.get("top_ads", [])
                row_usdt = {
                    "Date": localtime,
                    "Brand": bo_brand,
                    "Crypto": crypto_upper,
                    "Currency": reused_currency,
                    "USD": float(binance_usdtusd.get("data", {}).get("USDT", {}).get("price", 1.0)),
                    "XE RATE": round(xe_rate, 2) if xe_rate else None,
                    "BO Market Price": reused_bo_value,
                    "Binance Rate": round(p2p_usdt_result.get("binance_rate", 0), 2),
                    "Exchange Rate": round(exchange_rate, 2),
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
                "Exchange Rate": round(diff_percent, 2),
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
