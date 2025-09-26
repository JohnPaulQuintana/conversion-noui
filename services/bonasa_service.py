import requests
import traceback
from utils.env_loader import get_env


class BonasaService:
    def __init__(self):
        self.base_url = get_env("BONASA_BASE", "https://bo.bonasapoint.com")
        self.bonasa_login = get_env("BONASA_LOGIN_URL", "https://bo.bonasapoint.com/Login")
        self.bonasa_deposit = get_env("BONASA_DEPOSIT_URL", "https://bo.bonasapoint.com/DepositPaymentSetting")
        self.username = get_env("BONASA_USERNAME", "Summer")
        self.password = get_env("BONASA_PASSWORD", "888999Aaa")
        self.session = requests.Session()

    def _build_payload(self) -> dict:
        return {
            "username": self.username,
            "pass": self.password,
            "merchant": "BAJI"
        }
    
    def _build_headers(self) -> dict:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": self.base_url,
            "Referer": f"{self.bonasa_login}?merchant=BAJI",
        }
    
    # start authentication
    def authenticate(self, logger) -> bool:
        try:
            logger.info("→ Building Payload...")  
            payload = self._build_payload()
            logger.success("→ Building Payload Completed...")  

            logger.info("→ Building Header...")  
            headers = self._build_headers()
            logger.success("→ Building Header Completed...")  

            logger.info("→ Sending Network Calls...")  
            resp = self.session.post(self.bonasa_login, data=payload, headers=headers, verify=False)
            logger.success("→ Sending Network Calls Completed...")  

            # Always parse JSON (if possible)
            try:
                data = resp.json()
            except ValueError:
                logger.error("Response is not JSON")
                return False

            # Check for embedded error message
            if isinstance(data, dict) and "ErrorMsg" in data and data["ErrorMsg"]:
                logger.error(f"Authentication failed: {data['ErrorMsg']}")
                return False

            # If no error, assume success
            logger.success("Authentication successful")
            return True

        except Exception as e:
            logger.error(f"Error during authentication: {e}")
            traceback.print_exc()
            return False

        