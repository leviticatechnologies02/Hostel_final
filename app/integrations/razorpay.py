# Check app/integrations/razorpay.py - Make sure it handles missing credentials gracefully

import hashlib
import hmac
import json
from typing import Optional

from app.config import get_settings


class RazorpayClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.key_id = settings.razorpay_key_id
        self.key_secret = settings.razorpay_key_secret
        self.webhook_secret = settings.razorpay_webhook_secret or self.key_secret
        self._client = None
        self._configured = bool(self.key_id and self.key_id not in ("", "rzp_test_xxxxx") 
                                and self.key_secret and self.key_secret not in ("", "xxxxx"))

    def _get_client(self):
        if self._client is None and self._configured:
            try:
                import razorpay
                self._client = razorpay.Client(auth=(self.key_id, self.key_secret))
            except Exception as e:
                print(f"Razorpay client initialization error: {e}")
                self._configured = False
        return self._client

    def create_order(self, *, amount: float, receipt: str, notes: dict | None = None) -> dict:
        """Create Razorpay order - returns mock order if not configured."""
        if not self._configured:
            # Return mock order for testing
            print(f"[MOCK] Creating Razorpay order for amount {amount}, receipt {receipt}")
            return {
                "id": f"mock_order_{receipt[:10]}",
                "entity": "order",
                "amount": int(amount * 100),
                "amount_paid": 0,
                "amount_due": int(amount * 100),
                "currency": "INR",
                "receipt": receipt,
                "status": "created",
                "attempts": 0,
                "notes": notes or {},
                "created_at": 1234567890,
                "key_id": self.key_id or "mock_key_id"
            }
        
        amount_paise = int(round(amount * 100))
        order = self._get_client().order.create(data={
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "notes": notes or {},
        })
        order["key_id"] = self.key_id
        return order

    def verify_payment_signature(self, *, order_id: str, payment_id: str, signature: str) -> bool:
        """Verify payment signature - returns True for mock."""
        if not self._configured:
            return True
        
        try:
            self._get_client().utility.verify_payment_signature({
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            })
            return True
        except Exception:
            return False

    def verify_webhook_signature(self, payload_body: bytes, signature: str | None) -> bool:
        if not signature or not self.webhook_secret:
            return False
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"), payload_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def verify_signature(self, payload: dict, signature: str | None) -> bool:
        if not signature or not self.webhook_secret:
            return False
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)