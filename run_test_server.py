#!/usr/bin/env python3
"""Local test server with Stripe test mode keys and prices.

Usage:
    STRIPE_TEST_KEY=sk_test_... python3 run_test_server.py

Requires:
    - STRIPE_TEST_KEY env var (Stripe test secret key)
    - STRIPE_WEBHOOK_SECRET from the active ``stripe listen`` process
    - stripe listen --forward-to localhost:5050/webhook/stripe
      (in a separate terminal for webhook testing)
"""
import os
import secrets
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
PIPELINE_SCRIPTS_DIR = REPO_ROOT / 'athletes' / 'scripts'
TEST_DATA_ROOT = Path(
    os.environ.get('GG_TEST_DATA_DIR')
    or tempfile.mkdtemp(prefix='gg-stripe-test-')
).resolve()
PORT = int(os.environ.get('PORT', '5050'))

# Set test mode environment BEFORE importing the app
test_key = os.environ.get('STRIPE_TEST_KEY') or os.environ.get('STRIPE_SECRET_KEY')
if not test_key or not test_key.startswith('sk_test_'):
    print("ERROR: Set STRIPE_TEST_KEY env var to your Stripe test secret key")
    print("  STRIPE_TEST_KEY=sk_test_... python3 run_test_server.py")
    sys.exit(1)
webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '').strip()
if not webhook_secret.startswith('whsec_'):
    print("ERROR: Set STRIPE_WEBHOOK_SECRET from the active stripe listener")
    print("  stripe listen --events checkout.session.completed \\")
    print("    --forward-to http://127.0.0.1:5050/webhook/stripe")
    sys.exit(1)
os.environ['STRIPE_SECRET_KEY'] = test_key
os.environ['FLASK_ENV'] = 'development'
os.environ['ATHLETES_DIR'] = str(TEST_DATA_ROOT)
os.environ['DATA_DIR'] = str(TEST_DATA_ROOT)
os.environ['SCRIPTS_DIR'] = str(PIPELINE_SCRIPTS_DIR)
os.environ['REVIEW_BASE_URL'] = f'http://127.0.0.1:{PORT}'
for inherited_key in (
    'DOWNLOAD_TOKEN_KEYS', 'DOWNLOAD_TOKEN_KID',
    'DOWNLOAD_TOKEN_COACH_KID', 'DOWNLOAD_TOKEN_CUSTOMER_KID',
    'REVIEW_TOKEN_KEYS', 'REVIEW_TOKEN_KID',
):
    os.environ.pop(inherited_key, None)
os.environ['DOWNLOAD_TOKEN_SECRET'] = secrets.token_urlsafe(48)
os.environ['REVIEW_TOKEN_SECRET'] = secrets.token_urlsafe(48)

if not (PIPELINE_SCRIPTS_DIR / 'intake_to_plan.py').is_file():
    print(f"ERROR: Pipeline scripts not found at {PIPELINE_SCRIPTS_DIR}")
    sys.exit(1)

# Create temp output dirs. Executable pipeline code stays in the checkout.
os.makedirs(TEST_DATA_ROOT / '.logs', exist_ok=True)
os.makedirs(TEST_DATA_ROOT / 'intake', exist_ok=True)

# Add webhook dir to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'webhook'))

import webhook.app as app_module
import stripe

# Override Stripe key
stripe.api_key = os.environ['STRIPE_SECRET_KEY']

# Exercise the computed training-plan price as inline test-mode price data.
# Static test catalog IDs go stale and can make the canary fail before checkout.
app_module.TRAINING_PLAN_PRICE_IDS = {}

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
print("Training plan prices: computed inline (4-17+ weeks)")
print(f"Coaching prices: {len(app_module.COACHING_PRICE_IDS)} tiers")
print(f"Consulting price: {app_module.CONSULTING_PRICE_ID}")
print(f"Athletes dir: {os.environ['ATHLETES_DIR']}")
print(f"Pipeline scripts: {os.environ['SCRIPTS_DIR']}")
print()
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

app_module.app.run(host='127.0.0.1', port=PORT, debug=False,
                   use_reloader=False)
