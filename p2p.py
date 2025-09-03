import requests
import traceback

url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"

payload_template = {
    "fiat": "BDT",
    "rows": 10,
    "tradeType": "SELL",
    "asset": "USDT",
    "countries": [],
    "proMerchantAds": False,
    "shieldMerchantAds": False,
    "filterType": "all",
    "periods": [],
    "additionalKycVerifyFilter": 0,
    "publisherType": "merchant",
    "payTypes": [],
    "classifies": ["mass", "profession", "fiat_trade"],
    "tradedWith": False,
    "followed": False
}

all_ads = []

try:
    for page in range(1, 4):  # first 3 pages
        payload = payload_template.copy()
        payload["page"] = page

        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])

        for entry in data:
            adv = entry.get("adv", {})
            advertiser = entry.get("advertiser", {})

            all_ads.append({
                "price": float(adv.get("price")),
                "asset": adv.get("asset"),
                "fiat": payload["fiat"],
                "minAmount": adv.get("minSingleTransAmount"),
                "maxAmount": adv.get("dynamicMaxSingleTransAmount"),
                "available": adv.get("surplusAmount"),
                "tradeType": payload["tradeType"],
                "nick": advertiser.get("nickName"),
                "completionRate": advertiser.get("monthFinishRate"),
                "orders": advertiser.get("monthOrderCount", 0),
            })

    # Sort by highest orders
    top_ads = sorted(all_ads, key=lambda x: x["orders"], reverse=True)[:5]

    avg_rate = sum(ad["price"] for ad in top_ads) / len(top_ads)
    
    print(f"binance_rate {avg_rate}")
    print("\nTop 5 highest completed orders within first 3 pages:")
    for ad in top_ads:
        print(ad)

except Exception:
    print("⚠️ Error:\n" + traceback.format_exc())
