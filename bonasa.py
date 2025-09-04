import requests
import re
import json
import csv

LOGIN_URL = "https://bo.bonasapoint.com/Login"
DEPOSIT_URL = "https://bo.bonasapoint.com/DepositPaymentSetting"

payload = {
    "username": "Summer",
    "pass": "888999Aaa",
    "merchant": "BAJI"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://bo.bonasapoint.com",
    "Referer": "https://bo.bonasapoint.com/Login?merchant=BAJI",
}

session = requests.Session()

# Step 1: Login
resp = session.post(LOGIN_URL, data=payload, headers=headers, verify=False)
print("Login status:", resp.status_code)

# Step 2: Go to DepositPaymentSetting
deposit_page = session.get(DEPOSIT_URL, headers=headers, verify=False)
print("Deposit page status:", deposit_page.status_code)

html = deposit_page.text

# Step 3: Extract SerializeModel JSON from <script>
match = re.search(r"var\s+SerializeModel\s*=\s*(\{.*?\});", html, re.S)
if not match:
    print("⚠️ SerializeModel not found in page")
else:
    json_str = match.group(1)
    try:
        data = json.loads(json_str)
        rows = data.get("data", [])
        print(f"✅ Extracted {len(rows)} rows")

        # Save to CSV using csv.DictWriter
        if rows:
            keys = rows[0].keys()
            with open("deposit_payment_settings.csv", "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(rows)
            print("📂 Saved to deposit_payment_settings.csv")
        else:
            print("⚠️ No rows found in data")

    except Exception as e:
        print("❌ Error parsing JSON:", e)
