import httpx
import certifi
import asyncio
import logging
from utils.env_loader import get_env
# global
# BINANCE_URL = get_env("BINANCE_URL_GLOBAL", "https://api.binance.com/api/v3/ticker/price")
# US
BINANCE_URL = get_env("BINANCE_URL_US", "https://api.binance.us/api/v3/ticker/price")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def fetch_binance_price(symbol: str) -> dict:
    """
    Fetches Binance price for a given symbol.
    Returns a dict with:
        - status: "success" or "error"
        - data: JSON response on success
        - error: error message on failure
    """
    try:
        async with httpx.AsyncClient(verify=certifi.where(), timeout=10.0) as client:
            response = await client.get(BINANCE_URL, params={"symbol": symbol})
            response.raise_for_status()
            logger.info(f"Fetched {symbol} price successfully")
            return {"status": "success", "data": response.json(), "error": None}
    except httpx.ConnectError as e:
        logger.error(f"Connection error for {symbol}: {e}")
        return {"status": "error", "data": None, "error": str(e)}
    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error for {symbol}: {e.response.status_code} - {e.response.text}"
        )
        return {
            "status": "error",
            "data": None,
            "error": f"{e.response.status_code} - {e.response.text}",
        }
    except httpx.RequestError as e:
        logger.error(f"Request error for {symbol}: {e}")
        return {"status": "error", "data": None, "error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error for {symbol}: {e}")
        return {"status": "error", "data": None, "error": str(e)}


async def get_btc_eth_prices() -> dict:
    """
    Fetch BTC and ETH prices from Binance and return a unified status.
    """
    btc = await fetch_binance_price("BTCUSDT")
    eth = await fetch_binance_price("ETHUSDT")
    usdt_usd = await fetch_binance_price("USDTUSD")  # proxy for USDT/USD

    errors = []
    if btc.get("status") != "success":
        errors.append(f"BTC: {btc.get('error')}")
    if eth.get("status") != "success":
        errors.append(f"ETH: {eth.get('error')}")
    if usdt_usd.get("status") != "success":
        errors.append(f"ETH: {eth.get('error')}")

    if errors:
        return {
            "status": "error",
            "data": {"BTC": btc, "ETH": eth, "USDT_USD": usdt_usd},
            "error": "; ".join(errors),
        }

    return {"status": "success", "data": {"BTC": btc["data"], "ETH": eth["data"], "USDT": usdt_usd["data"]}, "error": None}


# ----------------------
# Entry point
# ----------------------
if __name__ == "__main__":
    async def main():
        result = await get_btc_eth_prices()
        print(result)

    asyncio.run(main())
