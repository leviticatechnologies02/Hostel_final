"""
Razorpay integration — production-ready implementation.
Handles order creation, payment signature verification, and webhook signature verification.
"""

import hashlib
import hmac
import json
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


class RazorpayClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.key_id = settings.razorpay_key_id
        self.key_secret = settings.razorpay_key_secret
        self.webhook_secret = settings.razorpay_webhook_secret or self.key_secret
        self._client = None
        self._configured = bool(
            self.key_id and self.key_id not in ("", "rzp_test_xxxxx", "rzp_live_xxxxx")
            and self.key_secret and self.key_secret not in ("", "xxxxx")
        )
        if self._configured:
            logger.info(f"[Razorpay] Configured with key: {self.key_id[:15]}...")
        else:
            logger.warning("[Razorpay] NOT configured — running in mock mode. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.")

    def _get_client(self):
        """Lazily initialize the razorpay SDK client."""
        if self._client is None and self._configured:
            try:
                import razorpay
                self._client = razorpay.Client(auth=(self.key_id, self.key_secret))
            except ImportError:
                logger.error("[Razorpay] razorpay package not installed. Run: pip install razorpay")
                self._configured = False
            except Exception as e:
                logger.error(f"[Razorpay] Client initialization error: {e}")
                self._configured = False
        return self._client

    def create_order(self, *, amount: float, receipt: str, notes: dict | None = None) -> dict:
        """
        Create a Razorpay order.
        - amount: amount in INR (will be converted to paise internally)
        - receipt: unique receipt identifier (booking number)
        - Returns full order dict including key_id for frontend checkout
        Falls back to a mock order if credentials are not configured.
        """
        if not self._configured:
            logger.warning(f"[Razorpay MOCK] Creating mock order — amount=₹{amount}, receipt={receipt}")
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
                "key_id": self.key_id or "mock_key_id",
            }

        amount_paise = int(round(amount * 100))
        try:
            order = self._get_client().order.create(data={
                "amount": amount_paise,
                "currency": "INR",
                "receipt": receipt,
                "notes": notes or {},
            })
            order["key_id"] = self.key_id  # Pass to frontend for checkout init
            logger.info(f"[Razorpay] Order created: {order['id']} for ₹{amount}")
            return order
        except Exception as e:
            logger.error(f"[Razorpay] Order creation failed: {e}")
            raise

    def verify_payment_signature(self, *, order_id: str, payment_id: str, signature: str) -> bool:
        """
        Verify the payment signature sent by Razorpay after successful payment.
        Called when frontend sends back razorpay_order_id, razorpay_payment_id, razorpay_signature.
        Returns True for mock mode.
        """
        if not self._configured:
            logger.warning("[Razorpay MOCK] Skipping signature verification (mock mode)")
            return True

        try:
            self._get_client().utility.verify_payment_signature({
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature,
            })
            logger.info(f"[Razorpay] Payment signature verified: {payment_id}")
            return True
        except Exception as e:
            logger.warning(f"[Razorpay] Payment signature verification FAILED: {e}")
            return False

    def verify_webhook_signature(self, payload_body: bytes, signature: str | None) -> bool:
        """
        Verify Razorpay webhook signature using HMAC-SHA256.
        payload_body: raw request bytes
        signature: value from X-Razorpay-Signature header
        """
        if not self.webhook_secret:
            logger.warning("[Razorpay] No webhook_secret configured — accepting all webhooks (insecure!)")
            return True  # Accept if no secret is set (dev mode)
        if not signature:
            logger.warning("[Razorpay] Webhook received without signature header")
            return False

        expected = hmac.new(
            self.webhook_secret.encode("utf-8"),
            payload_body,
            hashlib.sha256
        ).hexdigest()
        is_valid = hmac.compare_digest(expected, signature)
        if not is_valid:
            logger.warning("[Razorpay] Webhook signature mismatch — possible tampering!")
        return is_valid

    def verify_signature(self, payload: dict, signature: str | None) -> bool:
        """Fallback: verify signature from JSON-serialized dict (used when raw bytes unavailable)."""
        if not self.webhook_secret:
            return True
        if not signature:
            return False
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        expected = hmac.new(
            self.webhook_secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)