import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

async def fetch_binance_p2p_exact(fiat: str, max_pages: int = 3):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # headful helps mimic user
        context = await browser.new_context()
        page = await context.new_page()

        captured_request = {}

        async def handle_request(request):
            if "bapi/c2c/v2/friendly/c2c/adv/search" in request.url and request.method == "POST":
                if not captured_request:  # capture only the first one
                    captured_request["url"] = request.url
                    captured_request["headers"] = dict(request.headers)
                    try:
                        captured_request["post_data"] = request.post_data_json
                    except:
                        captured_request["post_data"] = json.loads(request.post_data or "{}")

        # Attach listener BEFORE navigating
        page.on("request", handle_request)

        # Now navigate (this will trigger the search request)
        await page.goto(f"https://p2p.binance.com/en/trade/sell/USDT?fiat={fiat}&payment=all-payments")
        await page.wait_for_load_state("networkidle")

        if not captured_request:
            raise RuntimeError("Could not capture the search request. Maybe the page changed or loaded too fast.")

        # Replay for multiple pages with captured headers/cookies
        all_pages = []
        for page_number in range(1, max_pages + 1):
            captured_request["post_data"]["page"] = page_number
            response = await context.request.post(
                captured_request["url"],
                data=json.dumps(captured_request["post_data"]),
                headers=captured_request["headers"]
            )
            all_pages.append(await response.json())

        await browser.close()
        return all_pages

async def main():
    fiat = "NPR"
    pages = await fetch_binance_p2p_exact(fiat, max_pages=3)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    raw_file = f"binance_p2p_raw_exact_{fiat}_{timestamp}.json"
    with open(raw_file, "w", encoding="utf-8") as f:
        json.dump({"pages": pages}, f, ensure_ascii=False, indent=4)
    print(f"✅ Saved exact network-matched result to {raw_file}")

if __name__ == "__main__":
    asyncio.run(main())
