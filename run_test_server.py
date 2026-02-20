#!/usr/bin/env python3
"""Local test server with Stripe test mode keys and prices.

Usage:
    STRIPE_TEST_KEY=sk_test_... python3 run_test_server.py

Requires:
    - STRIPE_TEST_KEY env var (Stripe test secret key)
    - stripe listen --forward-to localhost:5050/webhook/stripe
      (in a separate terminal for webhook testing)
"""
import os
import sys

# Set test mode environment BEFORE importing the app
test_key = os.environ.get('STRIPE_TEST_KEY') or os.environ.get('STRIPE_SECRET_KEY')
if not test_key or not test_key.startswith('sk_test_'):
    print("ERROR: Set STRIPE_TEST_KEY env var to your Stripe test secret key")
    print("  STRIPE_TEST_KEY=sk_test_... python3 run_test_server.py")
    sys.exit(1)
os.environ['STRIPE_SECRET_KEY'] = test_key
os.environ['FLASK_ENV'] = 'development'
os.environ['ATHLETES_DIR'] = '/tmp/gg-test-athletes'
os.environ['SCRIPTS_DIR'] = '/tmp/gg-test-athletes/scripts'

# Create temp dirs
os.makedirs('/tmp/gg-test-athletes/scripts', exist_ok=True)
os.makedirs('/tmp/gg-test-athletes/.logs', exist_ok=True)
os.makedirs('/tmp/gg-test-athletes/intake', exist_ok=True)

# Add webhook dir to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'webhook'))

import webhook.app as app_module
import stripe

# Override Stripe key
stripe.api_key = os.environ['STRIPE_SECRET_KEY']

# Override price IDs with test mode prices
app_module.TRAINING_PLAN_PRICE_IDS = {
    4: 'price_1T2wQdLoaHDbEqSqNeQ8J90v',
    5: 'price_1T2wQeLoaHDbEqSqIm981SFy',
    6: 'price_1T2wQeLoaHDbEqSqAIoet5hQ',
    7: 'price_1T2wQeLoaHDbEqSqWHjwRp9i',
    8: 'price_1T2wQeLoaHDbEqSqDv96E8Ww',
    9: 'price_1T2wQfLoaHDbEqSq2vx3qXab',
    10: 'price_1T2wQfLoaHDbEqSqZGFQjehW',
    11: 'price_1T2wQfLoaHDbEqSqOgidr42p',
    12: 'price_1T2wQfLoaHDbEqSqgoKjkMyQ',
    13: 'price_1T2wQgLoaHDbEqSqWTSEMScZ',
    14: 'price_1T2wQgLoaHDbEqSqYbldf2L8',
    15: 'price_1T2wQgLoaHDbEqSqJPlORxmJ',
    16: 'price_1T2wQhLoaHDbEqSqm4xAeEuF',
    17: 'price_1T2wQhLoaHDbEqSq5kxTi7HP',
}

app_module.COACHING_PRICE_IDS = {
    'min': 'price_1T2wQhLoaHDbEqSqUBXRAch9',
    'mid': 'price_1T2wQiLoaHDbEqSq4qQsPJmM',
    'max': 'price_1T2wQjLoaHDbEqSqx2yVYExY',
}

app_module.CONSULTING_PRICE_ID = 'price_1T2wQkLoaHDbEqSqlfEm2VEO'

app_module.COACHING_SETUP_FEE_PRICE_ID = 'price_1T2y2aLoaHDbEqSqafEZMdE0'  # $99 test mode

# Monkey-patch stripe.checkout.Session.create to strip consent_collection
# and after_expiration — test mode hasn't accepted the TOS for these.
_original_session_create = stripe.checkout.Session.create

@staticmethod
def _patched_session_create(**kwargs):
    kwargs.pop('consent_collection', None)
    kwargs.pop('after_expiration', None)
    return _original_session_create(**kwargs)

stripe.checkout.Session.create = _patched_session_create

print("=" * 60)
print("GRAVEL GOD TEST SERVER")
print("=" * 60)
print(f"Stripe mode: TEST")
print(f"Training plan prices: {len(app_module.TRAINING_PLAN_PRICE_IDS)} (4-17+ weeks)")
print(f"Coaching prices: {len(app_module.COACHING_PRICE_IDS)} tiers")
print(f"Consulting price: {app_module.CONSULTING_PRICE_ID}")
print(f"Athletes dir: {os.environ['ATHLETES_DIR']}")
print()
PORT = int(os.environ.get('PORT', '5050'))
print("Test endpoints:")
print(f"  POST http://localhost:{PORT}/api/create-checkout")
print(f"  POST http://localhost:{PORT}/api/create-coaching-checkout")
print(f"  POST http://localhost:{PORT}/api/create-consulting-checkout")
print(f"  GET  http://localhost:{PORT}/health")
print()
print("Test cards:")
print("  Success: 4242 4242 4242 4242")
print("  Decline: 4000 0000 0000 0002")
print("  3D Secure: 4000 0025 0000 3155")
print("  Exp: any future date, CVC: any 3 digits")
print("=" * 60)

app_module.app.run(host='0.0.0.0', port=PORT, debug=True)
