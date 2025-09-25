import asyncio
import random
from datetime import datetime
from services.bonasa_service import BonasaService
from utils.logger import Logger
from utils.spreadsheet import read_and_calculate_bonasa_sheet_tab, save_effective_conversion

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
    bonasa_service = BonasaService()
    auth_status = bonasa_service.authenticate(logger)
    if auth_status:
        rows = read_and_calculate_bonasa_sheet_tab(logger)
        if rows:
            print(rows)
            save_effective_conversion(logger, rows)
        else:
            logger.warning("⚠️ No rows to process")
    else:
        logger.error()
    
   

    

if __name__ == "__main__":
    asyncio.run(main())
