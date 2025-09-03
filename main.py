import asyncio
import random
from datetime import datetime
from services.binance_service import get_btc_eth_prices
from services.xe_service import fetch_xe_rates
from services.converter_service import convert_crypto_prices
from services.bo_scrapper_service import BOScrapperService
from services.binance_p2p_service import BinanceP2PService
from utils.logger import Logger

async def retry_async(func, *args, retries=5, min_wait=1, max_wait=5, logger=None, **kwargs):
    """
    Retry an async function until it succeeds or max retries is reached.
    Expects the function to return a dict with 'status' key.
    """
    attempt = 0
    while attempt < retries:
        result = await func(*args, **kwargs)
        if isinstance(result, dict) and result.get("status") == "success":
            return result
        attempt += 1
        wait_time = random.uniform(min_wait, max_wait)
        if logger:
            logger.warn(f"→ Attempt {attempt} failed for {func.__name__}. Retrying in {wait_time:.2f}s...")
        await asyncio.sleep(wait_time)

    if logger:
        logger.error(f"→ All {retries} attempts failed for {func.__name__}.")
    return result

async def main():
    logger = Logger()

    # Task 1: Binance (BTC/ETH) with retries
    binance_data = await retry_async(get_btc_eth_prices, retries=5, min_wait=2, max_wait=5, logger=logger)
    if binance_data.get("status") != "success":
        exit(f"→ Binance data fetch failed: {binance_data.get('error')}. Exiting.")

    logger.success(f"→ Binance data: {binance_data['data']}")

    # Task 2: XE conversion rates with retries
    xe_data = await retry_async(fetch_xe_rates, retries=5, min_wait=2, max_wait=5, logger=logger)
    if xe_data.get("status") != "success":
        exit(f"→ XE rates fetch failed: {xe_data.get('error')}. Exiting.")

    logger.success(f"→ XE rates: {xe_data['data'].get('rates', {})}")

    # Task 3: Conversion
    converted = convert_crypto_prices(
        binance_data.get("data", {}),
        xe_data.get("data", {})
    )
    logger.info("→ Converted Results:")
    logger.info(f"→ {converted.items()}")

    # Task 4: BO Scrapper
    service = BOScrapperService()
    if not service.test_accessible(logger):
        logger.warn("→ VPN REQUIRED TO ACCESS")
        exit("Check your VPN.")

    p2p_service = BinanceP2PService()

    localtime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    scrapper_response = service.scrappe_bo(logger, converted.items(), binance_data.get("data", {}), p2p_service, localtime)
    logger.info(f"→ isCompleted: {scrapper_response}")
    if scrapper_response:
        logger.success(f"→ {scrapper_response}")
    else:
        logger.error("→ Authentication failed.")

if __name__ == "__main__":
    asyncio.run(main())
