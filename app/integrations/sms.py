"""
2Factor.in SMS OTP Integration.
Sends OTP via SMS using the 2Factor Message API.
API Docs: https://2factor.in/API/V1/
"""

import logging
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

TWOFACTOR_BASE_URL = "https://2factor.in/API/V1"


class TwoFactorSMSClient:
    """Client for sending SMS OTP via 2Factor.in"""

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = settings.two_factor_api_key
        self._configured = bool(self.api_key and self.api_key not in ("", "your-2factor-api-key"))
        if self._configured:
            logger.info("[2Factor] SMS client configured.")
        else:
            logger.warning("[2Factor] NOT configured — SMS OTP will only be logged (dev mode). Set TWO_FACTOR_API_KEY.")

    def _normalize_phone(self, phone: str) -> str:
        """
        Normalize phone to 10-digit Indian number.
        Accepts: 9876543210, +919876543210, 919876543210
        Returns: 9876543210
        """
        import re
        cleaned = re.sub(r"[^0-9]", "", phone)
        if len(cleaned) == 12 and cleaned.startswith("91"):
            return cleaned[2:]
        if len(cleaned) == 11 and cleaned.startswith("0"):
            return cleaned[1:]
        return cleaned  # Assume 10-digit already

    async def send_otp(self, phone: str, otp: str) -> bool:
        """
        Send OTP via 2Factor SMS API.
        Uses the transactional SMS route:
          GET /API/V1/{API_KEY}/SMS/{PHONE}/{OTP}
        Returns True on success, False on failure.
        """
        phone_normalized = self._normalize_phone(phone)

        if not self._configured:
            logger.info(f"[2Factor MOCK] SMS OTP {otp} → {phone_normalized} (not configured)")
            print(f"[SMS OTP] {phone_normalized} → {otp}")
            return True

        url = f"{TWOFACTOR_BASE_URL}/{self.api_key}/SMS/{phone_normalized}/{otp}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                data = resp.json()
                if resp.status_code == 200 and data.get("Status") == "Success":
                    logger.info(f"[2Factor] OTP SMS sent to {phone_normalized}. Session: {data.get('Details')}")
                    return True
                else:
                    logger.error(f"[2Factor] Failed to send SMS to {phone_normalized}: {data}")
                    return False
        except Exception as e:
            logger.error(f"[2Factor] SMS send error for {phone_normalized}: {e}")
            return False

    async def send_otp_with_template(self, phone: str, otp: str, template_name: str) -> bool:
        """
        Send OTP using a custom approved DLT template.
        GET /API/V1/{API_KEY}/SMS/{PHONE}/{OTP}/{TEMPLATE_NAME}
        """
        phone_normalized = self._normalize_phone(phone)

        if not self._configured:
            logger.info(f"[2Factor MOCK] SMS OTP {otp} → {phone_normalized} (template={template_name})")
            print(f"[SMS OTP] {phone_normalized} → {otp} (template={template_name})")
            return True

        url = f"{TWOFACTOR_BASE_URL}/{self.api_key}/SMS/{phone_normalized}/{otp}/{template_name}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url)
                data = resp.json()
                if resp.status_code == 200 and data.get("Status") == "Success":
                    logger.info(f"[2Factor] Template SMS sent to {phone_normalized}. Session: {data.get('Details')}")
                    return True
                else:
                    logger.error(f"[2Factor] Template SMS failed to {phone_normalized}: {data}")
                    return False
        except Exception as e:
            logger.error(f"[2Factor] Template SMS error for {phone_normalized}: {e}")
            return False
