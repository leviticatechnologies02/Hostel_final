# scripts/verify_razorpay_keys.py
#!/usr/bin/env python3
"""Verify Razorpay API keys are working"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', '')

print("\n" + "="*60)
print("  RAZORPAY KEY VERIFICATION")
print("="*60)

if not RAZORPAY_KEY_ID:
    print("❌ RAZORPAY_KEY_ID not found in .env")
    sys.exit(1)

if not RAZORPAY_KEY_SECRET:
    print("❌ RAZORPAY_KEY_SECRET not found in .env")
    sys.exit(1)

print(f"\nKey ID: {RAZORPAY_KEY_ID[:20]}...")
print(f"Key Secret: {'*' * 16}")

try:
    import razorpay
    
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    
    # Try to create a test order (1 rupee)
    order = client.order.create({
        "amount": 100,  # 1 rupee in paise
        "currency": "INR",
        "receipt": "key_verification_test"
    })
    
    print("\n✅ Keys are VALID!")
    print(f"   Order ID: {order['id']}")
    print(f"   Amount: ₹{order['amount']/100}")
    print(f"   Status: {order['status']}")
    
except Exception as e:
    print(f"\n❌ Keys are INVALID: {e}")
    print("\nTo fix:")
    print("1. Go to https://dashboard.razorpay.com/")
    print("2. Settings → API Keys")
    print("3. Generate new test keys")
    print("4. Update .env file")
    sys.exit(1)