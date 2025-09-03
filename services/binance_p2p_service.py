import requests
import traceback
from utils.env_loader import get_env


class BinanceP2PService:
    def __init__(self):
        self.base_url = get_env(
            "P2P_URL", "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        )
        self.session = requests.Session()

    def _build_payload(self, fiat: str, page: int) -> dict:
        return {
            "fiat": fiat,
            "page": page,
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
            "followed": False,
        }

    def fetch_top5_completed_order_rates(self, fiat: str) -> dict:
        all_ads = []

        try:
            for page in range(1, 4):  # first 3 pages
                payload = self._build_payload(fiat, page)
                resp = self.session.post(self.base_url, json=payload, timeout=10)
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

            if not top_ads:
                return {"status": "error", "message": "No ads found"}

            avg_rate = sum(ad["price"] for ad in top_ads) / len(top_ads)

            return {
                "status": "success",
                "fiat": fiat,
                "asset": "USDT",
                "binance_rate": avg_rate,
                "sign": "Positive" if avg_rate >= 0 else "Negative",
                "top_ads": top_ads,
            }

        except Exception:
            return {"status": "error", "message": traceback.format_exc()}
