import requests
from bs4 import BeautifulSoup

LOGIN_URL = "https://bo.bonasapoint.com/Login"
DEPOSIT_URL = "https://bo.bonasapoint.com/DepositPaymentSetting"

payload = {
    "username": "Summer",
    "pass": "888999Aaa",
    "merchant": "BAJI"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://bo.bonasapoint.com",
    "Referer": "https://bo.bonasapoint.com/Login?merchant=BAJI",
}

# Start a session
session = requests.Session()

# Step 1: Login
resp = session.post(LOGIN_URL, data=payload, headers=headers, verify=False)
print("Login status:", resp.status_code)

# Step 2: Go to DepositPaymentSetting
deposit_page = session.get(DEPOSIT_URL, headers=headers)
print("Deposit page status:", deposit_page.status_code)

# Step 3: Parse with BeautifulSoup
soup = BeautifulSoup(deposit_page.text, "html.parser")

# Example: extract table rows
tables = soup.find_all("table")
for idx, table in enumerate(tables):
    print(f"\n--- Table {idx+1} ---")
    for row in table.find_all("tr"):
        cols = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
        print(cols)
