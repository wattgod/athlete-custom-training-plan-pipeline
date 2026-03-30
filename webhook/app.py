"""
Gravel God Webhook Receiver

Receives Stripe webhooks after successful payment,
creates Stripe Checkout Sessions from questionnaire data,
triggers the training plan pipeline, and delivers to athlete.

Deploy to: Railway
"""

import os
import re
import json
import hmac
import fcntl
import hashlib
import logging
import subprocess
import uuid
import math
import shutil
import zipfile
import base64
import requests as http_requests
from pathlib import Path
from datetime import datetime, timedelta, date
from flask import Flask, request, jsonify, send_file
from flask_limiter import Limiter
import stripe
import yaml

app = Flask(__name__)


def _get_real_ip():
    """Get client IP, handling Railway/proxy X-Forwarded-For."""
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'


limiter = Limiter(
    key_func=_get_real_ip,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

# =============================================================================
# LOGGING
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('gravel-god-webhook')

# =============================================================================
# CONFIGURATION - Fail fast if critical config missing in production
# =============================================================================

IS_PRODUCTION = os.environ.get('FLASK_ENV') == 'production'

WOOCOMMERCE_SECRET = os.environ.get('WOOCOMMERCE_SECRET', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
ATHLETES_DIR = os.environ.get('ATHLETES_DIR', '/app/athletes')
SCRIPTS_DIR = os.environ.get('SCRIPTS_DIR', '/app/athletes/scripts')
DATA_DIR = os.environ.get('DATA_DIR', ATHLETES_DIR)  # Persistent volume for intake/logs
DELIVERIES_DIR = os.path.join(DATA_DIR, 'deliveries')  # Persistent: zipped plans for download

# CORS — only allow requests from our site
ALLOWED_ORIGINS = ['https://gravelgodcycling.com', 'https://www.gravelgodcycling.com']

# Email notifications for new orders
NOTIFICATION_EMAIL = os.environ.get('NOTIFICATION_EMAIL', '')
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
RESEND_FROM = os.environ.get('RESEND_FROM', 'Gravel God <noreply@gravelgodcycling.com>')

# Configure Stripe
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# Validate required config in production
if IS_PRODUCTION:
    if not STRIPE_WEBHOOK_SECRET:
        logger.warning("STRIPE_WEBHOOK_SECRET not set — webhook verification disabled")
    if not STRIPE_SECRET_KEY:
        raise RuntimeError("STRIPE_SECRET_KEY required in production")

# Pricing — $15/week computed from race date, capped at $249
PRICE_PER_WEEK_CENTS = 1500   # $15/week
PRICE_CAP_CENTS = 24900       # $249 max
MIN_WEEKS = 4                 # Minimum 4 weeks ($60)
STRIPE_PRODUCT_NAME = 'Custom Training Plan'

# Pre-built Stripe price IDs (from scripts/create_stripe_products.py)
# Training plan prices keyed by weeks (4–16, plus 17+ cap)
TRAINING_PLAN_PRICE_IDS = {
    4: 'price_1T2ekOLoaHDbEqSqRbpy02qh',
    5: 'price_1T2ekOLoaHDbEqSqpJx9E1yq',
    6: 'price_1T2ekOLoaHDbEqSqY1A8y6LK',
    7: 'price_1T2ekPLoaHDbEqSq7mnndDhP',
    8: 'price_1T2ekPLoaHDbEqSqevidiXbx',
    9: 'price_1T2ekPLoaHDbEqSqkTTpr9dN',
    10: 'price_1T2ekQLoaHDbEqSqJr4wjnF8',
    11: 'price_1T2ekQLoaHDbEqSqJFJBGMkS',
    12: 'price_1T2ekQLoaHDbEqSqScrmfxRF',
    13: 'price_1T2ekQLoaHDbEqSqZ4o7bj8B',
    14: 'price_1T2ekRLoaHDbEqSq3q1cniEc',
    15: 'price_1T2ekRLoaHDbEqSqzhPHsmaP',
    16: 'price_1T2ekRLoaHDbEqSqFXGSA95u',
    17: 'price_1T2ekRLoaHDbEqSqgQVjT7FI',  # 17+ weeks (cap)
}

COACHING_PRICE_IDS = {
    'min': 'price_1T2z58LoaHDbEqSqeb8lLS9g',   # $199/4wk
    'mid': 'price_1T2z6SLoaHDbEqSqQIChOlOn',   # $299/4wk
    'max': 'price_1T2z7MLoaHDbEqSqoWpedvF5',   # $1,200/4wk
}

# One-time $99 setup fee added to all coaching checkouts
COACHING_SETUP_FEE_PRICE_ID = 'price_1T2yzQLoaHDbEqSqXKe6gNuF'  # $99 one-time (live)
COACHING_SETUP_FEE_CENTS = 9900

CONSULTING_PRICE_ID = 'price_1T2ekVLoaHDbEqSq0GGfoBEX'  # $150/hr

# Stripe Tax — requires Stripe Tax to be enabled at account level first.
# Set ENABLE_AUTOMATIC_TAX=true in Railway env vars after completing Stripe Tax setup.
ENABLE_AUTOMATIC_TAX = os.environ.get('ENABLE_AUTOMATIC_TAX', '').lower() == 'true'

# Intake data expiry (24 hours)
INTAKE_EXPIRY_HOURS = None  # Never auto-delete — intake data is tiny and needed for retries

# Checkout session expiry — short expiry triggers Stripe's recovery flow sooner
CHECKOUT_EXPIRY_MINUTES = 60

# Cron endpoint secret (prevents unauthorized triggers)
CRON_SECRET = os.environ.get('CRON_SECRET', '')

# Pipeline timeout (5 minutes)
PIPELINE_TIMEOUT = 300

# =============================================================================
# SECURITY HEADERS
# =============================================================================

@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # CORS for checkout API (questionnaire form submits cross-origin)
    origin = request.headers.get('Origin', '')
    if origin in ALLOWED_ORIGINS or not IS_PRODUCTION:
        response.headers['Access-Control-Allow-Origin'] = origin or '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'

    return response


# =============================================================================
# PERIODIC CLEANUP
# =============================================================================

_last_intake_cleanup = datetime.now()


@app.before_request
def _periodic_intake_cleanup():
    """Clean stale intake files hourly, not just on startup."""
    global _last_intake_cleanup
    now = datetime.now()
    if (now - _last_intake_cleanup).total_seconds() > 3600:
        _last_intake_cleanup = now
        try:
            cleanup_stale_intakes()
        except Exception as e:
            logger.warning(f"Periodic intake cleanup failed: {e}")


# =============================================================================
# INPUT VALIDATION
# =============================================================================

# Strict athlete ID pattern
ATHLETE_ID_PATTERN = re.compile(r'^[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]$|^[a-z0-9]$')
MAX_ATHLETE_ID_LENGTH = 64
MAX_NAME_LENGTH = 100


def validate_athlete_id(athlete_id: str) -> bool:
    """Validate athlete ID is safe for filesystem use."""
    if not athlete_id:
        return False
    if len(athlete_id) > MAX_ATHLETE_ID_LENGTH:
        return False
    if not ATHLETE_ID_PATTERN.match(athlete_id):
        return False
    if '..' in athlete_id or '/' in athlete_id or '\\' in athlete_id:
        return False
    return True


def sanitize_athlete_id(name: str) -> str:
    """Convert a name to a safe athlete ID."""
    if not name or len(name) > MAX_NAME_LENGTH:
        return ''
    safe_id = name.lower().strip()
    safe_id = re.sub(r'\s+', '_', safe_id)
    safe_id = re.sub(r'[^a-z0-9_-]', '', safe_id)
    safe_id = re.sub(r'_+', '_', safe_id)
    safe_id = safe_id.strip('_-')
    safe_id = safe_id[:MAX_ATHLETE_ID_LENGTH]
    return safe_id


def _mask_email(email: str) -> str:
    """Mask email for safe logging: 'user@example.com' → 'u***@e***.com'"""
    if not email or '@' not in email:
        return '***'
    local, domain = email.rsplit('@', 1)
    parts = domain.rsplit('.', 1)
    masked_local = local[0] + '***' if local else '***'
    masked_domain = parts[0][0] + '***' if parts[0] else '***'
    tld = '.' + parts[1] if len(parts) > 1 else ''
    return f'{masked_local}@{masked_domain}{tld}'


def _send_email(to: str, subject: str, body: str, html: str = None, reply_to: str = None):
    """Send email via Resend HTTP API. Returns True on success."""
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not configured — cannot send email")
        return False

    payload = {
        'from': RESEND_FROM,
        'to': [to],
        'subject': subject,
        'text': body,
    }
    if html:
        payload['html'] = html
    if reply_to:
        payload['reply_to'] = reply_to

    try:
        resp = http_requests.post(
            'https://api.resend.com/emails',
            headers={'Authorization': f'Bearer {RESEND_API_KEY}'},
            json=payload,
            timeout=10,
        )
        if resp.status_code == 200:
            logger.info(f"Email sent: {subject} → {_mask_email(to)}")
            return True
        else:
            logger.error(f"Resend API error {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Failed to send email via Resend: {e}")
        return False


def _build_training_plan_email(details: dict) -> tuple:
    """Build coach notification email — athlete info + step-by-step fulfillment checklist."""
    name = details.get('name', 'Unknown')
    email = details.get('email', '')
    tier = details.get('tier', 'custom')
    order_id = details.get('order_id', '')
    race_name = details.get('race_name', '')
    race_date = details.get('race_date', '')
    ftp = details.get('ftp', '')
    weight_kg = details.get('weight_kg', '')
    hours = details.get('hours_per_week', '')
    weeks = details.get('plan_weeks', '')
    workouts = details.get('workout_count', '')
    methodology = details.get('methodology', '')
    athlete_id = details.get('athlete_id', '')
    pipeline_ok = details.get('pipeline_success', True)
    error_msg = details.get('error', '')
    download_token = details.get('download_token', '')

    base_url = 'https://athlete-custom-training-plan-pipeline-production.up.railway.app'
    download_full = f'{base_url}/api/download/{athlete_id}?type=full&token={download_token}' if download_token else ''

    status_color = '#1A8A82' if pipeline_ok else '#c0392b'
    status_label = 'READY FOR REVIEW' if pipeline_ok else 'PIPELINE FAILED'

    subject = f"[GG] {'New order' if pipeline_ok else 'FAILED'}: {name} — {race_name or 'training plan'}"

    # Shared athlete + plan info block
    info_html = f"""
    <h3 style="margin: 0 0 12px; font-size: 15px; color: #59473c;">Athlete</h3>
    <table style="font-size: 14px; border-collapse: collapse; width: 100%;">
      <tr><td style="padding: 4px 12px 4px 0; color: #888; width: 120px;">Name</td><td style="padding: 4px 0;"><strong>{name}</strong></td></tr>
      <tr><td style="padding: 4px 12px 4px 0; color: #888;">Email</td><td style="padding: 4px 0;"><a href="mailto:{email}">{email}</a></td></tr>
      {'<tr><td style="padding: 4px 12px 4px 0; color: #888;">FTP</td><td style="padding: 4px 0;">' + str(ftp) + 'W</td></tr>' if ftp else ''}
      {'<tr><td style="padding: 4px 12px 4px 0; color: #888;">Weight</td><td style="padding: 4px 0;">' + str(weight_kg) + ' kg</td></tr>' if weight_kg else ''}
      {'<tr><td style="padding: 4px 12px 4px 0; color: #888;">Hours/week</td><td style="padding: 4px 0;">' + str(hours) + '</td></tr>' if hours else ''}
    </table>

    <h3 style="margin: 20px 0 12px; font-size: 15px; color: #59473c;">Plan</h3>
    <table style="font-size: 14px; border-collapse: collapse; width: 100%;">
      {'<tr><td style="padding: 4px 12px 4px 0; color: #888; width: 120px;">Race</td><td style="padding: 4px 0;"><strong>' + race_name + '</strong></td></tr>' if race_name else ''}
      {'<tr><td style="padding: 4px 12px 4px 0; color: #888;">Race date</td><td style="padding: 4px 0;">' + race_date + '</td></tr>' if race_date else ''}
      {'<tr><td style="padding: 4px 12px 4px 0; color: #888;">Duration</td><td style="padding: 4px 0;">' + str(weeks) + ' weeks</td></tr>' if weeks else ''}
      {'<tr><td style="padding: 4px 12px 4px 0; color: #888;">Workouts</td><td style="padding: 4px 0;">' + str(workouts) + ' ZWO files</td></tr>' if workouts else ''}
      {'<tr><td style="padding: 4px 12px 4px 0; color: #888;">Methodology</td><td style="padding: 4px 0;">' + methodology + '</td></tr>' if methodology else ''}
    </table>"""

    if pipeline_ok:
        html = f"""
<div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
  <div style="background: {status_color}; color: white; padding: 16px 24px; border-radius: 4px 4px 0 0;">
    <h2 style="margin: 0; font-size: 18px;">{status_label}: {name}</h2>
    <p style="margin: 4px 0 0; opacity: 0.9; font-size: 14px;">{race_name} &middot; {tier} tier</p>
  </div>

  <div style="background: #f9f9f7; padding: 24px; border: 1px solid #e0e0e0; border-top: none;">
    {info_html}

    {'<div style="margin: 24px 0; text-align: center;"><a href="' + download_full + '" style="display: inline-block; background: #59473c; color: white; padding: 14px 28px; text-decoration: none; border-radius: 4px; font-size: 15px; font-weight: bold;">Download Full Package</a></div>' if download_full else ''}

    <h3 style="margin: 24px 0 12px; font-size: 15px; color: #59473c;">Fulfillment checklist</h3>
    <ol style="font-size: 14px; padding-left: 20px; line-height: 2.0;">
      <li><strong>Download the package</strong> (button above)</li>
      <li><strong>Review quality</strong> — open <code>plan_preview.html</code>, check the week grid and quality gates</li>
      <li><strong>Read coaching brief</strong> — <code>coaching_brief.md</code> maps questionnaire answers to plan decisions</li>
      <li><strong>Spot-check workouts</strong> — open <code>training_guide.html</code>, check weeks 1, mid, and final</li>
      <li><strong>Create athlete in TrainingPeaks</strong> — add <a href="mailto:{email}">{name}</a> to your coach account</li>
      <li><strong>Import ZWO files</strong> — drag workouts into their TP calendar, starting week 1</li>
      <li><strong>Send confirmation email</strong> — let them know the plan is live on TrainingPeaks:<br>
        <code style="font-size: 12px; background: #f0ede8; padding: 4px 8px; border-radius: 3px; display: inline-block; margin-top: 4px;">curl -X POST {base_url}/api/confirm/{athlete_id} -H "X-Cron-Secret: $CRON_SECRET"</code></li>
    </ol>

    <div style="margin: 20px 0; padding: 12px 16px; background: #fff; border-left: 3px solid #B7950B;">
      <p style="margin: 0; font-size: 13px; color: #666;">
        <strong>Timeline:</strong> Customer got a payment confirmation email automatically. They're expecting the plan within 24 hours. Don't let it sit.
      </p>
    </div>

    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 24px 0 16px;">
    <p style="font-size: 12px; color: #999; margin: 0;">
      Athlete ID: {athlete_id} &middot; Order: {order_id}<br>
      Pipeline: passed &middot; {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
    </p>
  </div>
</div>"""
    else:
        html = f"""
<div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
  <div style="background: {status_color}; color: white; padding: 16px 24px; border-radius: 4px 4px 0 0;">
    <h2 style="margin: 0; font-size: 18px;">PIPELINE FAILED: {name}</h2>
    <p style="margin: 4px 0 0; opacity: 0.9; font-size: 14px;">{race_name} &middot; Order {order_id}</p>
  </div>

  <div style="background: #f9f9f7; padding: 24px; border: 1px solid #e0e0e0; border-top: none;">
    {info_html}

    <div style="margin: 20px 0; padding: 16px; background: #fdf2f2; border: 1px solid #e8c4c4; border-radius: 4px;">
      <h3 style="margin: 0 0 8px; font-size: 15px; color: #c0392b;">Error</h3>
      <pre style="font-size: 12px; white-space: pre-wrap; margin: 0; color: #666;">{error_msg or 'Check Railway logs for details.'}</pre>
    </div>

    <h3 style="margin: 20px 0 12px; font-size: 15px; color: #59473c;">Recovery steps</h3>
    <ol style="font-size: 14px; padding-left: 20px; line-height: 2.0;">
      <li><strong>Check Railway logs</strong>: <code>railway logs --service stripe-webhook</code></li>
      <li><strong>Fix the issue</strong>, re-run locally: <code>pbpaste | python3 intake_to_plan.py</code></li>
      <li><strong>Email {name}</strong> — let them know there's a short delay, don't ghost them</li>
    </ol>

    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 24px 0 16px;">
    <p style="font-size: 12px; color: #999; margin: 0;">
      Athlete ID: {athlete_id} &middot; Order: {order_id}<br>
      Pipeline: FAILED &middot; {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}
    </p>
  </div>
</div>"""

    # Plain text fallback
    text = f"""{'READY FOR REVIEW' if pipeline_ok else 'PIPELINE FAILED'}: {name}
Race: {race_name} ({race_date})
Tier: {tier} | FTP: {ftp}W | Hours: {hours}/wk
Plan: {weeks} weeks, {workouts} workouts
Methodology: {methodology}
Order: {order_id} | Athlete ID: {athlete_id}
{'Download: ' + download_full if download_full else ''}

{'Fulfillment checklist:' if pipeline_ok else 'Recovery steps:'}
"""
    if pipeline_ok:
        text += f"""1. Download the package (link above)
2. Review plan_preview.html — check week grid and quality gates
3. Read coaching_brief.md — questionnaire-to-decision trace
4. Spot-check training_guide.html (weeks 1, mid, final)
5. Create {name} in TrainingPeaks, add to coach account
6. Import ZWO files into their TP calendar
7. Send confirmation: curl -X POST {base_url}/api/confirm/{athlete_id} -H "X-Cron-Secret: $CRON_SECRET"

Timeline: Customer got payment confirmation. They expect the plan within 24h.
"""
    else:
        text += f"""1. Check Railway logs: railway logs --service stripe-webhook
2. Fix the issue, re-run locally: pbpaste | python3 intake_to_plan.py
3. Email {name} — let them know there's a short delay

ERROR: {error_msg}
"""
    return subject, text, html


def _build_coaching_email(details: dict) -> tuple:
    """Build subject + HTML for a coaching subscription notification."""
    name = details.get('name', 'Unknown')
    email = details.get('email', '')
    tier = details.get('tier', 'unknown')
    subscription_id = details.get('subscription_id', '')
    order_id = details.get('order_id', '')

    subject = f"[GG] New coaching: {name} — {tier} tier"
    html = f"""
<div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
  <div style="background: #59473c; color: white; padding: 16px 24px; border-radius: 4px 4px 0 0;">
    <h2 style="margin: 0; font-size: 18px;">New coaching: {name}</h2>
    <p style="margin: 4px 0 0; opacity: 0.9; font-size: 14px;">{tier} tier &middot; Order {order_id}</p>
  </div>
  <div style="background: #f9f9f7; padding: 24px; border: 1px solid #e0e0e0; border-top: none;">
    <table style="font-size: 14px; border-collapse: collapse; width: 100%;">
      <tr><td style="padding: 4px 12px 4px 0; color: #888;">Name</td><td><strong>{name}</strong></td></tr>
      <tr><td style="padding: 4px 12px 4px 0; color: #888;">Email</td><td><a href="mailto:{email}">{email}</a></td></tr>
      <tr><td style="padding: 4px 12px 4px 0; color: #888;">Tier</td><td>{tier}</td></tr>
      <tr><td style="padding: 4px 12px 4px 0; color: #888;">Subscription</td><td><code>{subscription_id}</code></td></tr>
    </table>
    <h3 style="margin: 20px 0 12px; font-size: 15px; color: #59473c;">Next steps</h3>
    <ol style="font-size: 14px; padding-left: 20px; line-height: 1.8;">
      <li>Send welcome email to <a href="mailto:{email}">{name}</a> within 24 hours</li>
      <li>Schedule intake call</li>
      <li>Set up TrainingPeaks shared calendar</li>
    </ol>
  </div>
</div>"""
    text = f"New coaching: {name} ({email}), {tier} tier, subscription {subscription_id}, order {order_id}"
    return subject, text, html


def _build_consulting_email(details: dict) -> tuple:
    """Build subject + HTML for a consulting booking notification."""
    name = details.get('name', 'Unknown')
    email = details.get('email', '')
    hours = details.get('hours', '1')
    order_id = details.get('order_id', '')

    subject = f"[GG] Consulting booked: {name} — {hours}hr"
    html = f"""
<div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
  <div style="background: #B7950B; color: white; padding: 16px 24px; border-radius: 4px 4px 0 0;">
    <h2 style="margin: 0; font-size: 18px;">Consulting: {name}</h2>
    <p style="margin: 4px 0 0; opacity: 0.9; font-size: 14px;">{hours} hour(s) &middot; Order {order_id}</p>
  </div>
  <div style="background: #f9f9f7; padding: 24px; border: 1px solid #e0e0e0; border-top: none;">
    <table style="font-size: 14px; border-collapse: collapse; width: 100%;">
      <tr><td style="padding: 4px 12px 4px 0; color: #888;">Name</td><td><strong>{name}</strong></td></tr>
      <tr><td style="padding: 4px 12px 4px 0; color: #888;">Email</td><td><a href="mailto:{email}">{email}</a></td></tr>
      <tr><td style="padding: 4px 12px 4px 0; color: #888;">Hours</td><td>{hours}</td></tr>
    </table>
    <h3 style="margin: 20px 0 12px; font-size: 15px; color: #59473c;">Next steps</h3>
    <ol style="font-size: 14px; padding-left: 20px; line-height: 1.8;">
      <li>Email <a href="mailto:{email}">{name}</a> to schedule the call</li>
      <li>Send calendar invite with video link</li>
    </ol>
  </div>
</div>"""
    text = f"Consulting booked: {name} ({email}), {hours}hr, order {order_id}"
    return subject, text, html


def _notify_new_order(product_type: str, details: dict):
    """Send rich notification for new order. Falls back to CRITICAL log if Resend not configured."""
    if product_type in ('training_plan', 'training_plan_FAILED'):
        details['pipeline_success'] = product_type == 'training_plan'
        subject, text, html = _build_training_plan_email(details)
    elif product_type == 'coaching':
        subject, text, html = _build_coaching_email(details)
    elif product_type == 'consulting':
        subject, text, html = _build_consulting_email(details)
    else:
        # Fallback for TEST and unknown types
        subject = f"[Gravel God] {product_type}: {details.get('name', 'Unknown')}"
        text = '\n'.join(f"  {k}: {v}" for k, v in details.items())
        html = None

    if NOTIFICATION_EMAIL and RESEND_API_KEY:
        if not _send_email(NOTIFICATION_EMAIL, subject, text, html=html):
            logger.critical(f"NEW ORDER: {subject}\n{text}")
    else:
        logger.critical(f"NEW ORDER: {subject}\n{text}")


def _send_payment_confirmation(customer_email: str, customer_name: str,
                               race_name: str = '', plan_weeks: str = ''):
    """Send immediate payment confirmation to customer.

    Auto-fires on successful Stripe checkout. Tells them what they bought,
    that we're building their plan, and when to expect it.
    """
    if not RESEND_API_KEY:
        logger.warning("Cannot send payment confirmation — RESEND_API_KEY not set")
        return

    first_name = customer_name.split()[0] if customer_name else 'there'
    race_mention = f' for {race_name}' if race_name else ''
    weeks_mention = f'{plan_weeks}-week ' if plan_weeks else ''

    subject = f'Payment confirmed — your {weeks_mention}training plan{race_mention}'

    text = f"""Hey {first_name},

Payment received — thank you. Here's what happens next:

1. Your custom {weeks_mention}training plan{race_mention} is being built right now.
2. I'll review it personally to make sure everything checks out.
3. You'll get an invite to connect on TrainingPeaks — that's where your plan lives.
4. Expect everything to be ready within 24 hours.

You don't need to do anything yet. I'll email you when the plan is live on TrainingPeaks.

If you have questions in the meantime, reply to this email.

— Matt, Gravel God Cycling
gravelgodcycling.com
"""

    html = f"""
<div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
  <div style="background: #59473c; color: white; padding: 24px; border-radius: 4px 4px 0 0;">
    <h1 style="margin: 0; font-size: 22px;">Payment confirmed</h1>
    <p style="margin: 6px 0 0; opacity: 0.9; font-size: 15px;">{weeks_mention}training plan{race_mention}</p>
  </div>

  <div style="background: #f9f9f7; padding: 24px; border: 1px solid #e0e0e0; border-top: none;">
    <p style="font-size: 15px; line-height: 1.6;">Hey {first_name},</p>

    <p style="font-size: 15px; line-height: 1.6;">Payment received — thank you. Here's what happens next:</p>

    <ol style="font-size: 14px; padding-left: 20px; line-height: 2.2;">
      <li>Your custom {weeks_mention}training plan{race_mention} is <strong>being built right now</strong>.</li>
      <li>I'll <strong>review it personally</strong> to make sure everything checks out.</li>
      <li>You'll get an invite to connect on <strong>TrainingPeaks</strong> — that's where your plan lives.</li>
      <li>Expect everything to be <strong>ready within 24 hours</strong>.</li>
    </ol>

    <div style="margin: 24px 0; padding: 16px; background: #fff; border-left: 3px solid #1A8A82;">
      <p style="margin: 0; font-size: 14px; color: #555;">You don't need to do anything yet. I'll email you when the plan is live on TrainingPeaks.</p>
    </div>

    <p style="font-size: 14px; line-height: 1.6;">Questions in the meantime? Reply to this email.</p>

    <p style="font-size: 14px; margin-top: 24px; color: #666;">— Matt, Gravel God Cycling<br>
    <a href="https://gravelgodcycling.com" style="color: #1A8A82;">gravelgodcycling.com</a></p>
  </div>
</div>"""

    ok = _send_email(customer_email, subject, text, html=html, reply_to=NOTIFICATION_EMAIL)
    if ok:
        logger.info(f"Payment confirmation sent to {_mask_email(customer_email)}")
    else:
        logger.error(f"Failed to send payment confirmation to {_mask_email(customer_email)}")


def _build_plan_notification_details(order_data: dict, result: dict,
                                     intake_data: dict = None) -> dict:
    """Build enriched details dict for training plan notifications."""
    profile = order_data.get('profile', {})
    fitness = profile.get('fitness_markers', {})
    target = profile.get('target_race', {})
    schedule = profile.get('weekly_schedule', {})

    # Parse workout count from pipeline stdout
    stdout = result.get('stdout', '')
    workout_count = ''
    for line in stdout.split('\n'):
        if '.zwo files' in line:
            # e.g. "  workouts/            145 .zwo files"
            parts = line.strip().split()
            for i, p in enumerate(parts):
                if p == '.zwo':
                    workout_count = parts[i - 1] if i > 0 else ''
                    break

    # Parse plan weeks from stdout
    plan_weeks = ''
    for line in stdout.split('\n'):
        if '-week plan' in line:
            for word in line.split():
                if word.endswith('-week'):
                    plan_weeks = word.replace('-week', '')
                    break

    # Try to get methodology from athlete dir
    methodology = ''
    athlete_id = order_data.get('athlete_id', '')
    meth_path = Path(ATHLETES_DIR) / athlete_id / 'methodology.yaml'
    if meth_path.exists():
        try:
            import yaml
            with open(meth_path) as f:
                meth_data = yaml.safe_load(f)
                methodology = meth_data.get('name', meth_data.get('methodology', ''))
        except Exception:
            pass

    return {
        'name': profile.get('name', ''),
        'email': profile.get('email', ''),
        'tier': order_data.get('tier', 'custom'),
        'order_id': order_data.get('order_id', ''),
        'athlete_id': athlete_id,
        'race_name': target.get('name', intake_data.get('race_name', '') if intake_data else ''),
        'race_date': target.get('date', intake_data.get('race_date', '') if intake_data else ''),
        'ftp': fitness.get('ftp_watts', intake_data.get('ftp', '') if intake_data else ''),
        'weight_kg': fitness.get('weight_kg', ''),
        'hours_per_week': (schedule.get('hours_per_week', '')
                          or schedule.get('cycling_hours_target', '')
                          or (intake_data.get('hours_per_week', '') if intake_data else '')),
        'plan_weeks': plan_weeks,
        'workout_count': workout_count,
        'methodology': methodology,
        'error': result.get('stderr', '')[:500] if not result.get('success') else '',
    }


def _log_product_event(product_type: str, order_id: str, **details):
    """Write a product event to the order log. Shared by coaching/consulting handlers."""
    log_dir = Path(DATA_DIR) / '.logs'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"{datetime.now().strftime('%Y-%m')}.jsonl"
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'product_type': product_type,
        'order_id': order_id,
        **details,
        'success': True,
    }
    try:
        with open(log_file, 'a') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(json.dumps(log_entry) + '\n')
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except IOError as e:
        logger.error(f"Failed to write {product_type} log: {e}")


def validate_order_data(order_data: dict) -> tuple:
    """Validate order data, return (is_valid, error_message)."""
    athlete_id = order_data.get('athlete_id', '')
    if not validate_athlete_id(athlete_id):
        return False, f"Invalid athlete ID: {athlete_id}"

    profile = order_data.get('profile', {})
    if not profile.get('name'):
        return False, "Missing athlete name"

    if not profile.get('email'):
        return False, "Missing athlete email"

    # Validate email format loosely
    email = profile.get('email', '')
    if '@' not in email or '.' not in email:
        return False, f"Invalid email format: {email}"

    # Validate numeric fields if present
    fitness = profile.get('fitness_markers', {})
    if fitness.get('weight_kg') is not None:
        weight = fitness['weight_kg']
        if not (30 <= weight <= 200):
            return False, f"Invalid weight: {weight}"

    if fitness.get('ftp_watts') is not None:
        ftp = fitness['ftp_watts']
        if not (50 <= ftp <= 600):
            return False, f"Invalid FTP: {ftp}"

    return True, None


# =============================================================================
# SIGNATURE VERIFICATION
# =============================================================================

def verify_woocommerce_signature(payload: bytes, signature: str) -> bool:
    """Verify WooCommerce webhook signature."""
    if not WOOCOMMERCE_SECRET:
        if IS_PRODUCTION:
            logger.error("WOOCOMMERCE_SECRET not configured in production")
            return False
        logger.warning("WOOCOMMERCE_SECRET not set - skipping verification (dev mode)")
        return True

    expected = hmac.new(
        WOOCOMMERCE_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    # WooCommerce sends base64 encoded signature, not hex
    import base64
    try:
        sig_bytes = base64.b64decode(signature)
        sig_hex = sig_bytes.hex()
    except Exception:
        sig_hex = signature  # Fallback to raw comparison

    return hmac.compare_digest(expected, sig_hex)


def verify_stripe_signature(payload: bytes, signature: str) -> bool:
    """Verify Stripe webhook signature."""
    if not STRIPE_WEBHOOK_SECRET:
        if IS_PRODUCTION:
            logger.error("STRIPE_WEBHOOK_SECRET not configured in production")
            return False
        logger.warning("STRIPE_WEBHOOK_SECRET not set - skipping verification (dev mode)")
        return True

    try:
        stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)
        return True
    except stripe.error.SignatureVerificationError as e:
        logger.warning(f"Stripe signature verification failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Stripe verification error: {e}")
        return False


# =============================================================================
# IDEMPOTENCY
# =============================================================================

def check_idempotency(order_id: str) -> bool:
    """Check if this order has already been processed. Returns True if duplicate."""
    if not order_id:
        return False

    processed_file = Path(DATA_DIR) / '.processed_orders.json'

    try:
        if processed_file.exists():
            with open(processed_file, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                processed = json.load(f)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                if order_id in processed:
                    logger.info(f"Duplicate order detected: {order_id}")
                    return True
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Error reading processed orders: {e}")

    return False


def mark_order_processed(order_id: str, athlete_id: str):
    """Mark an order as processed."""
    if not order_id:
        return

    processed_file = Path(DATA_DIR) / '.processed_orders.json'
    processed_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(processed_file, 'a+') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.seek(0)
            try:
                processed = json.load(f)
            except json.JSONDecodeError:
                processed = {}

            processed[order_id] = {
                'athlete_id': athlete_id,
                'processed_at': datetime.now().isoformat()
            }

            f.seek(0)
            f.truncate()
            json.dump(processed, f, indent=2)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except IOError as e:
        logger.error(f"Error marking order processed: {e}")


# =============================================================================
# INTAKE STORAGE — Questionnaire data stored temporarily before payment
# =============================================================================

def get_intake_dir() -> Path:
    """Get or create the intake storage directory on persistent volume."""
    intake_dir = Path(DATA_DIR) / '.intake'
    intake_dir.mkdir(parents=True, exist_ok=True)
    return intake_dir


def store_intake(intake_id: str, data: dict):
    """Store questionnaire data for later retrieval after payment."""
    intake_dir = get_intake_dir()
    intake_file = intake_dir / f'{intake_id}.json'

    with open(intake_file, 'w') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        json.dump({
            'intake_id': intake_id,
            'stored_at': datetime.now().isoformat(),
            'data': data,
        }, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    logger.info(f"Stored intake {intake_id}")


def load_intake(intake_id: str) -> dict:
    """Load stored questionnaire data. Returns empty dict if not found."""
    # Validate intake_id is a valid UUID to prevent path traversal
    try:
        uuid.UUID(intake_id)
    except (ValueError, AttributeError):
        logger.warning(f"Invalid intake_id format: {intake_id}")
        return {}

    intake_file = get_intake_dir() / f'{intake_id}.json'
    if not intake_file.exists():
        logger.warning(f"Intake not found: {intake_id}")
        return {}

    try:
        with open(intake_file, 'r') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            content = json.load(f)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return content.get('data', {})
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading intake {intake_id}: {e}")
        return {}


def cleanup_stale_intakes():
    """No-op. Intake files are kept permanently — they're small and needed for retries."""
    pass


# =============================================================================
# PRICE COMPUTATION
# =============================================================================

def compute_plan_price(race_date_str: str) -> dict:
    """Compute plan price based on weeks until A-race.

    Returns dict with weeks, price_cents, price_display.
    $15/week, minimum 4 weeks ($60), capped at $249.
    """
    try:
        race_date = datetime.strptime(race_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        # If no valid date, use minimum price
        return {
            'weeks': MIN_WEEKS,
            'price_cents': MIN_WEEKS * PRICE_PER_WEEK_CENTS,
            'price_display': f'${MIN_WEEKS * PRICE_PER_WEEK_CENTS // 100}',
        }

    today = date.today()
    days_until = (race_date - today).days
    weeks = max(MIN_WEEKS, math.ceil(days_until / 7))

    price_cents = min(weeks * PRICE_PER_WEEK_CENTS, PRICE_CAP_CENTS)

    return {
        'weeks': weeks,
        'price_cents': price_cents,
        'price_display': f'${price_cents // 100}',
    }


# =============================================================================
# DATA EXTRACTION
# =============================================================================

def extract_woocommerce_data(data: dict) -> dict:
    """Extract athlete info from WooCommerce order."""
    billing = data.get('billing', {})
    meta = {item['key']: item['value'] for item in data.get('meta_data', [])}
    line_items = data.get('line_items', [])

    # Determine tier from product SKU (more reliable than name)
    tier = 'race_ready'  # default
    for item in line_items:
        sku = item.get('sku', '').lower()
        if sku == 'training-starter':
            tier = 'starter'
        elif sku == 'training-full-build':
            tier = 'full_build'
        elif sku == 'training-race-ready':
            tier = 'race_ready'
        else:
            # Fallback to name matching
            product_name = item.get('name', '').lower()
            if 'starter' in product_name:
                tier = 'starter'
            elif 'full' in product_name and 'build' in product_name:
                tier = 'full_build'

    # Generate athlete ID from name
    first_name = billing.get('first_name', '').strip()
    last_name = billing.get('last_name', '').strip()
    name = f"{first_name} {last_name}".strip()
    athlete_id = sanitize_athlete_id(name)

    return {
        'athlete_id': athlete_id,
        'order_id': str(data.get('id', '')),
        'tier': tier,
        'profile': {
            'name': name,
            'email': billing.get('email', '').strip().lower(),
            'age': safe_int(meta.get('age')),
            'fitness_markers': {
                'weight_kg': safe_float(meta.get('weight_kg')),
                'ftp_watts': safe_int(meta.get('ftp_watts')),
            },
            'target_race': {
                'name': meta.get('race_name', ''),
                'date': meta.get('race_date', ''),
                'distance_miles': safe_float(meta.get('race_distance_miles')),
                'elevation_gain_ft': safe_int(meta.get('race_elevation_ft')),
                'terrain': meta.get('race_terrain', 'gravel'),
            },
            'weekly_schedule': {
                'cycling_hours_target': safe_float(meta.get('cycling_hours', 10)),
                'strength_hours': safe_float(meta.get('strength_hours', 2)),
                'preferred_long_day': meta.get('preferred_long_day', 'saturday'),
            },
            'experience_level': meta.get('experience_level', 'intermediate'),
            'race_goal': meta.get('race_goal', 'finish'),
            'limiters': meta.get('limiters', ''),
            'notes': meta.get('notes', ''),
        }
    }


def extract_stripe_data(data: dict) -> dict:
    """Extract athlete info from Stripe checkout session.

    If an intake_id is present in metadata, loads the full questionnaire
    data from the intake store (rich data from the form). Otherwise falls
    back to extracting from Stripe metadata (sparse).
    """
    session = data.get('data', {}).get('object', {})
    metadata = session.get('metadata', {})
    customer_details = session.get('customer_details', {})

    # Check for intake data from questionnaire flow
    intake_id = metadata.get('intake_id', '')
    intake_data = load_intake(intake_id) if intake_id else {}

    name = (
        intake_data.get('name')
        or customer_details.get('name', metadata.get('name', 'Unknown'))
    ).strip()
    athlete_id = sanitize_athlete_id(name)

    email = (
        intake_data.get('email')
        or customer_details.get('email', '')
    ).strip().lower()

    # Tier from metadata — computed pricing model uses 'custom' as default
    tier = metadata.get('tier', 'custom')

    # Build profile — intake data provides the rich questionnaire fields
    if intake_data:
        # Convert weight from lbs to kg if provided
        weight_lbs = safe_float(intake_data.get('weight'))
        weight_kg = round(weight_lbs * 0.453592, 1) if weight_lbs else None

        profile = {
            'name': name,
            'email': email,
            'sex': intake_data.get('sex', ''),
            'age': safe_int(intake_data.get('age')),
            'fitness_markers': {
                'weight_kg': weight_kg,
                'ftp_watts': safe_int(intake_data.get('ftp')),
                'hr_max': safe_int(intake_data.get('hr_max')),
                'hr_threshold': safe_int(intake_data.get('hr_threshold')),
                'hr_resting': safe_int(intake_data.get('hr_resting')),
                'power_or_hr': intake_data.get('powerOrHr', ''),
                'pw_ratio': intake_data.get('pwRatio', ''),
            },
            'target_race': {
                'name': intake_data.get('race_name', ''),
                'date': intake_data.get('race_date', ''),
                'distance_miles': intake_data.get('race_distance', ''),
                'goal': intake_data.get('race_goal', ''),
            },
            'races': intake_data.get('races', []),
            'weekly_schedule': {
                'hours_per_week': intake_data.get('hours_per_week', ''),
                'trainer_access': intake_data.get('trainer_access', ''),
                'long_ride_days': intake_data.get('long_ride_days', []),
                'interval_days': intake_data.get('interval_days', []),
                'off_days': intake_data.get('off_days', []),
            },
            'strength': {
                'current': intake_data.get('strength_current', ''),
                'want': intake_data.get('strength_want', ''),
                'equipment': intake_data.get('strength_equipment', ''),
            },
            'experience_level': intake_data.get('years_cycling', ''),
            'sleep_quality': intake_data.get('sleep_quality', ''),
            'stress_level': intake_data.get('stress_level', ''),
            'injuries': intake_data.get('injuries', ''),
            'notes': intake_data.get('notes', ''),
            'blindspots': intake_data.get('blindspots', []),
        }
    else:
        # Sparse fallback from Stripe metadata only
        profile = {
            'name': name,
            'email': email,
            'age': safe_int(metadata.get('age')),
            'fitness_markers': {
                'weight_kg': safe_float(metadata.get('weight_kg')),
                'ftp_watts': safe_int(metadata.get('ftp_watts')),
            },
            'target_race': {
                'name': metadata.get('race_name', ''),
                'date': metadata.get('race_date', ''),
                'distance_miles': safe_float(metadata.get('race_distance_miles')),
                'elevation_gain_ft': safe_int(metadata.get('race_elevation_ft')),
                'terrain': metadata.get('race_terrain', 'gravel'),
            },
            'weekly_schedule': {
                'cycling_hours_target': safe_float(metadata.get('cycling_hours', 10)),
                'strength_hours': safe_float(metadata.get('strength_hours', 2)),
                'preferred_long_day': metadata.get('preferred_long_day', 'saturday'),
            },
            'experience_level': metadata.get('experience_level', 'intermediate'),
            'race_goal': metadata.get('race_goal', 'finish'),
            'limiters': metadata.get('limiters', ''),
            'notes': metadata.get('notes', ''),
        }

    return {
        'athlete_id': athlete_id,
        'order_id': session.get('id', ''),
        'tier': tier,
        'profile': profile,
    }


def safe_int(val):
    """Safely convert to int with bounds checking."""
    try:
        if val is None or val == '':
            return None
        result = int(val)
        # Sanity bounds
        if result < 0 or result > 100000:
            return None
        return result
    except (ValueError, TypeError):
        return None


def safe_float(val):
    """Safely convert to float with bounds checking."""
    try:
        if val is None or val == '':
            return None
        result = float(val)
        # Sanity bounds
        if result < 0 or result > 100000:
            return None
        return result
    except (ValueError, TypeError):
        return None


# =============================================================================
# PROFILE CREATION (with file locking)
# =============================================================================

def create_athlete_profile(order_data: dict) -> tuple:
    """Create athlete profile YAML from order data with atomic write."""
    athlete_id = order_data['athlete_id']
    athlete_dir = Path(ATHLETES_DIR) / athlete_id
    athlete_dir.mkdir(parents=True, exist_ok=True)

    profile = order_data['profile'].copy()
    profile['tier'] = order_data['tier']
    profile['order_id'] = order_data['order_id']
    profile['created_at'] = datetime.now().isoformat()

    profile_path = athlete_dir / 'profile.yaml'
    temp_path = athlete_dir / '.profile.yaml.tmp'

    # Atomic write with file locking
    try:
        with open(temp_path, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            yaml.dump(profile, f, default_flow_style=False, sort_keys=False)
            f.flush()
            os.fsync(f.fileno())
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        # Atomic rename
        temp_path.rename(profile_path)

    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise e

    return athlete_id, profile_path


# =============================================================================
# PIPELINE EXECUTION
# =============================================================================

def _questionnaire_to_markdown(intake_data: dict, name: str = '', email: str = '') -> str:
    """Convert web questionnaire JSON into the markdown format intake_to_plan.py expects."""
    name = name or intake_data.get('name', 'Unknown Athlete')
    email = email or intake_data.get('email', '')

    # Build race list
    races = intake_data.get('races', [])
    race_lines = []
    for r in races:
        priority = r.get('priority', 'A')
        race_lines.append(f"  {r.get('name', 'Unknown')} ({r.get('date', 'TBD')}, "
                          f"{r.get('distance', '~100 mi')}, priority {priority})")

    # Map long_ride_days/interval_days/off_days
    long_days = ', '.join(intake_data.get('long_ride_days', ['Saturday']))
    interval_days = ', '.join(intake_data.get('interval_days', ['Tuesday', 'Thursday']))
    off_days = ', '.join(intake_data.get('off_days', []))

    # Height
    height_ft = intake_data.get('height_ft', '')
    height_in = intake_data.get('height_in', '')
    height_str = f"{height_ft}'{height_in}\"" if height_ft else ''

    # Goal mapping
    goal_map = {'Survive': 'finish', 'Finish Strong': 'finish', 'Compete': 'compete', 'Podium': 'podium'}
    a_race = next((r for r in races if r.get('priority') == 'A'), races[0] if races else {})
    goal = goal_map.get(a_race.get('goal', ''), 'finish')

    md = f"""# Athlete Intake: {name}
Email: {email}
Submitted: {datetime.now().strftime('%Y-%m-%d')}

## Basic Info
- Sex: {intake_data.get('sex', 'Male')}
- Age: {intake_data.get('age', '')}
- Weight: {intake_data.get('weight', '')} lbs
- Height: {height_str}

## Goals
- Primary Goal: specific_race
- Races:
{chr(10).join(race_lines)}
- Success: {a_race.get('goal', 'finish')}

## Current Fitness
- FTP: {intake_data.get('ftp', 'unknown')}
- HR Max: {intake_data.get('hr_max', '')}
- HR Threshold: {intake_data.get('hr_threshold', '')}
- W/kg: {intake_data.get('pwRatio', '')}
- Years Cycling: {intake_data.get('years_cycling', '3')}
- Years Structured: {intake_data.get('prior_plan_experience', '1')}
- Longest Recent Ride: {intake_data.get('longest_ride', '3-4 hrs')}

## Recovery & Baselines
- Resting HR: {intake_data.get('hr_resting', '')}
- Typical Sleep: {intake_data.get('sleep_quality', '7 hours')}
- Sleep Quality: {intake_data.get('sleep_quality', 'good')}

## Equipment
- Indoor Trainer: {intake_data.get('trainer_access', 'smart trainer')}
- Devices: power meter, HR strap

## Schedule
- Weekly Hours Available: {intake_data.get('hours_per_week', '10')}
- Current Volume: {intake_data.get('hours_per_week', '8')}
- Long Ride Days: {long_days}
- Interval Days: {interval_days}
- Off Days: {off_days or 'None'}

## Strength
- Current: {intake_data.get('strength_current', 'none')}
- Include: {intake_data.get('strength_want', 'no')}
- Equipment: {intake_data.get('strength_equipment', 'minimal')}

## Health
- Current Injuries: {intake_data.get('injuries', 'None')}

## Work & Life
- Life Stress: {intake_data.get('stress_level', 'moderate')}

## Additional
- Other: {intake_data.get('notes', '')}
"""
    return md


def run_pipeline(athlete_id: str, deliver: bool = True, intake_data: dict = None) -> dict:
    """Run the full training plan pipeline via intake_to_plan.py."""
    script_path = Path(SCRIPTS_DIR) / 'intake_to_plan.py'

    # Fallback to generate_full_package.py if no intake data (legacy path)
    if not intake_data:
        script_path = Path(SCRIPTS_DIR) / 'generate_full_package.py'
        if not script_path.exists():
            return {
                'success': False,
                'stdout': '',
                'stderr': f'Pipeline script not found: {script_path}'
            }
        cmd = ['python3', str(script_path), athlete_id]
        if deliver:
            cmd.append('--deliver')
        logger.info(f"Running legacy pipeline for {athlete_id}")
    else:
        if not script_path.exists():
            return {
                'success': False,
                'stdout': '',
                'stderr': f'Pipeline script not found: {script_path}'
            }
        cmd = ['python3', str(script_path)]
        logger.info(f"Running intake pipeline for {athlete_id}")

    # Generate markdown input for intake pipeline
    stdin_data = None
    if intake_data:
        name = intake_data.get('name', '')
        email = intake_data.get('email', '')
        stdin_data = _questionnaire_to_markdown(intake_data, name=name, email=email)
        logger.info(f"Generated {len(stdin_data)} char markdown intake for {athlete_id}")

    try:
        result = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=PIPELINE_TIMEOUT,
            cwd=SCRIPTS_DIR,
            env={**os.environ, 'GG_AUTO_EMAIL': 'true'}
        )

        success = result.returncode == 0
        if success:
            logger.info(f"Pipeline succeeded for {athlete_id}")
        else:
            logger.error(f"Pipeline failed for {athlete_id}: {result.stderr[:500]}")

        return {
            'success': success,
            'stdout': result.stdout,
            'stderr': result.stderr,
        }

    except subprocess.TimeoutExpired:
        logger.error(f"Pipeline timeout for {athlete_id}")
        return {
            'success': False,
            'stdout': '',
            'stderr': f'Pipeline timed out after {PIPELINE_TIMEOUT}s'
        }
    except subprocess.SubprocessError as e:
        logger.error(f"Pipeline subprocess error for {athlete_id}: {e}")
        return {
            'success': False,
            'stdout': '',
            'stderr': str(e)
        }


# =============================================================================
# DELIVERY PERSISTENCE — zip deliverables to persistent volume
# =============================================================================

# Files the customer gets (order matters for zip listing)
CUSTOMER_DELIVERABLES = [
    'training_guide.html',
    'training_guide.pdf',
    'dashboard.html',
    'plan_preview.html',
    'fueling.yaml',
]
# Coach-only files (not sent to customer)
COACH_DELIVERABLES = [
    'coaching_brief.md',
    'plan_summary.yaml',
    'profile.yaml',
    'methodology.yaml',
    'derived.yaml',
    'intake_backup.json',
]


def persist_deliverables(athlete_id: str) -> dict:
    """Copy deliverables from ephemeral athlete dir to persistent volume and create zip.

    Returns dict with delivery_dir, zip_path, customer_zip_path, and file counts.
    Customer zip excludes coach-only files (coaching_brief, profile, methodology).
    """
    # Handle underscore/hyphen mismatch between webhook (sam_delgado) and
    # intake_to_plan.py (sam-delgado). Check both conventions.
    athlete_dir = Path(ATHLETES_DIR) / athlete_id
    alt_id = athlete_id.replace('_', '-')
    alt_dir = Path(ATHLETES_DIR) / alt_id

    if not athlete_dir.exists() and alt_dir.exists():
        athlete_dir = alt_dir
    elif not athlete_dir.exists():
        # Try finding any matching directory
        for d in Path(ATHLETES_DIR).iterdir():
            if d.is_dir() and d.name.replace('-', '_') == athlete_id.replace('-', '_'):
                athlete_dir = d
                break

    delivery_dir = Path(DELIVERIES_DIR) / athlete_id
    delivery_dir.mkdir(parents=True, exist_ok=True)

    copied = []
    missing = []

    # Also check the ~/Downloads path (where intake_to_plan.py copies curated files)
    downloads_dir = Path.home() / 'Downloads' / f'{alt_id}-training-plan'
    if not downloads_dir.exists():
        downloads_dir = Path.home() / 'Downloads' / f'{athlete_id}-training-plan'
    source_dir = downloads_dir if downloads_dir.exists() else athlete_dir

    # Copy workouts/
    workouts_src = source_dir / 'workouts'
    if not workouts_src.exists():
        workouts_src = athlete_dir / 'workouts'
    if workouts_src.exists():
        workouts_dst = delivery_dir / 'workouts'
        if workouts_dst.exists():
            shutil.rmtree(workouts_dst)
        shutil.copytree(workouts_src, workouts_dst)
        zwo_count = len(list(workouts_dst.glob('*.zwo')))
        copied.append(f'workouts/ ({zwo_count} .zwo files)')
    else:
        missing.append('workouts/')

    # Copy individual files
    for fname in CUSTOMER_DELIVERABLES + COACH_DELIVERABLES:
        src = source_dir / fname
        if not src.exists():
            src = athlete_dir / fname  # Fallback to raw athlete dir
        if src.exists():
            shutil.copy2(src, delivery_dir / fname)
            copied.append(fname)
        elif fname in ('training_guide.pdf',):
            pass  # PDF is optional (no Chrome on Railway)
        else:
            missing.append(fname)

    # Create FULL zip (coach — everything)
    full_zip = delivery_dir / f'{athlete_id}-full-package.zip'
    _create_zip(delivery_dir, full_zip, exclude_zip=True)

    # Create CUSTOMER zip (no coach-only files)
    customer_zip = delivery_dir / f'{athlete_id}-training-plan.zip'
    _create_zip(delivery_dir, customer_zip, exclude_zip=True,
                exclude_files=set(COACH_DELIVERABLES))

    logger.info(f"Persisted deliverables for {athlete_id}: "
                f"{len(copied)} files, full={full_zip.stat().st_size // 1024}KB, "
                f"customer={customer_zip.stat().st_size // 1024}KB")

    return {
        'delivery_dir': str(delivery_dir),
        'full_zip': str(full_zip),
        'customer_zip': str(customer_zip),
        'full_zip_size': full_zip.stat().st_size,
        'customer_zip_size': customer_zip.stat().st_size,
        'copied': copied,
        'missing': missing,
    }


def _create_zip(source_dir: Path, zip_path: Path, exclude_zip: bool = True,
                exclude_files: set = None):
    """Create a zip file from source_dir contents."""
    exclude_files = exclude_files or set()
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(source_dir.rglob('*')):
            if item.is_file():
                rel = item.relative_to(source_dir)
                if exclude_zip and item.suffix == '.zip':
                    continue
                if rel.name in exclude_files:
                    continue
                zf.write(item, rel)


def _normalize_athlete_id(athlete_id: str) -> str:
    """Normalize athlete_id for consistent token generation (underscore form)."""
    return athlete_id.replace('-', '_')


def _generate_download_token(athlete_id: str) -> str:
    """Generate a signed download token for an athlete's deliverables.

    Token = HMAC-SHA256(CRON_SECRET, athlete_id:date). Valid for 30 days.
    """
    secret = os.environ.get('CRON_SECRET', 'dev-secret')
    date_str = datetime.now().strftime('%Y-%m')  # Monthly rotation
    payload = f'{_normalize_athlete_id(athlete_id)}:{date_str}'
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]


def _verify_download_token(athlete_id: str, token: str) -> bool:
    """Verify a download token. Checks current and previous month."""
    secret = os.environ.get('CRON_SECRET', 'dev-secret')
    norm_id = _normalize_athlete_id(athlete_id)
    for delta_months in (0, -1):
        d = date.today().replace(day=1)
        if delta_months:
            d = d - timedelta(days=1)  # Last day of previous month
        date_str = d.strftime('%Y-%m')
        payload = f'{norm_id}:{date_str}'
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
        if hmac.compare_digest(token, expected):
            return True
    return False


# =============================================================================
# LOGGING
# =============================================================================

def log_order(order_data: dict, result: dict):
    """Log order processing for tracking with file locking.

    Includes email, name, product_type so follow-up email system can find orders.
    """
    log_dir = Path(DATA_DIR) / '.logs'
    log_dir.mkdir(exist_ok=True)

    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'product_type': 'training_plan',
        'athlete_id': order_data['athlete_id'],
        'order_id': order_data['order_id'],
        'tier': order_data['tier'],
        'email': order_data.get('profile', {}).get('email', ''),
        'name': order_data.get('profile', {}).get('name', ''),
        'success': result['success'],
        'error': result.get('stderr', '')[:500] if not result['success'] else None,
    }

    log_file = log_dir / f"{datetime.now().strftime('%Y-%m')}.jsonl"

    try:
        with open(log_file, 'a') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(json.dumps(log_entry) + '\n')
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except IOError as e:
        logger.error(f"Failed to write log: {e}")


# =============================================================================
# ROUTES
# =============================================================================

@app.route('/api/test-notification', methods=['POST'])
def test_notification():
    """Send a test notification email to verify SMTP config. TEMPORARY — remove after testing."""
    data = request.get_json() or {}
    _notify_new_order('TEST', {
        'name': 'Notification Test',
        'email': 'test@test.com',
        'race': 'Test Race',
        'note': 'This is a test notification to verify SMTP works.',
    })
    return jsonify({'status': 'sent', 'to': NOTIFICATION_EMAIL, 'provider': 'resend'})




@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint with dependency checks."""
    checks = {
        'service': 'gravel-god-webhook',
        'status': 'ok',
        'athletes_dir': Path(ATHLETES_DIR).exists(),
        'scripts_dir': Path(SCRIPTS_DIR).exists(),
        'data_dir': Path(DATA_DIR).exists(),
    }

    if not checks['athletes_dir'] or not checks['scripts_dir']:
        checks['status'] = 'degraded'

    status_code = 200 if checks['status'] == 'ok' else 503
    return jsonify(checks), status_code


# =============================================================================
# DELIVERY ENDPOINTS — download zips, send to customer
# =============================================================================

@app.route('/api/download/<athlete_id>', methods=['GET'])
def download_deliverables(athlete_id):
    """Download an athlete's deliverables zip.

    Auth: either X-Cron-Secret header OR ?token= signed URL parameter.
    Query params:
      ?type=customer (default) — customer-facing zip (no coach files)
      ?type=full — full package including coaching_brief, profile, etc.
    """
    # Auth: header secret or signed token
    secret = request.headers.get('X-Cron-Secret', '')
    token = request.args.get('token', '')
    has_secret = secret and hmac.compare_digest(secret, os.environ.get('CRON_SECRET', ''))
    has_token = token and _verify_download_token(athlete_id, token)

    if not has_secret and not has_token:
        return jsonify({'error': 'Unauthorized'}), 401

    # Normalize — accept both underscore and hyphen forms
    norm_id = _normalize_athlete_id(athlete_id)
    if not validate_athlete_id(norm_id):
        return jsonify({'error': 'Invalid athlete ID'}), 400

    zip_type = request.args.get('type', 'customer')
    delivery_dir = Path(DELIVERIES_DIR) / norm_id

    if zip_type == 'full':
        zip_path = delivery_dir / f'{norm_id}-full-package.zip'
    else:
        zip_path = delivery_dir / f'{norm_id}-training-plan.zip'

    if not zip_path.exists():
        return jsonify({'error': 'Deliverables not found. Pipeline may not have run yet.'}), 404

    return send_file(
        zip_path,
        mimetype='application/zip',
        as_attachment=True,
        download_name=zip_path.name,
    )


@app.route('/api/confirm/<athlete_id>', methods=['POST'])
def confirm_plan_ready(athlete_id):
    """Send "your plan is live on TrainingPeaks" email to customer.

    Coach triggers this AFTER reviewing the plan and importing to TP.
    Secured by X-Cron-Secret.
    """
    secret = request.headers.get('X-Cron-Secret', '')
    if not secret or not hmac.compare_digest(secret, os.environ.get('CRON_SECRET', '')):
        return jsonify({'error': 'Unauthorized'}), 401

    norm_id = _normalize_athlete_id(athlete_id)
    if not validate_athlete_id(norm_id):
        return jsonify({'error': 'Invalid athlete ID'}), 400

    # Find customer email and race from order logs
    log_dir = Path(DATA_DIR) / '.logs'
    customer_email = None
    customer_name = None
    race_name = None
    plan_weeks = None

    for log_file in sorted(log_dir.glob('*.jsonl'), reverse=True):
        try:
            with open(log_file) as f:
                for line in f:
                    entry = json.loads(line.strip())
                    if (entry.get('athlete_id', '').replace('-', '_') == norm_id
                            and entry.get('success')):
                        customer_email = entry.get('email', '')
                        customer_name = entry.get('name', '')
                        break
        except (json.JSONDecodeError, IOError):
            continue
        if customer_email:
            break

    if not customer_email:
        return jsonify({'error': 'Customer email not found in order logs'}), 404

    # Load intake backup for race details
    delivery_dir = Path(DELIVERIES_DIR) / norm_id
    intake_backup = delivery_dir / 'intake_backup.json'
    if intake_backup.exists():
        try:
            with open(intake_backup) as f:
                backup = json.load(f)
                race_name = backup.get('race_name', '')
        except Exception:
            pass

    first_name = customer_name.split()[0] if customer_name else 'there'
    race_mention = f' for {race_name}' if race_name else ''

    subject = f'Your training plan{race_mention} is live on TrainingPeaks'

    text_body = f"""Hey {first_name},

Your custom training plan{race_mention} is built, reviewed, and live on TrainingPeaks.

Here's what to do:
1. Log in to TrainingPeaks — you should have a coach invite from me. Accept it.
2. Your calendar now has every workout loaded, day by day, through race week.
3. Each workout has target power zones, duration, and structure — just follow the plan.
4. Do today's workout. Don't overthink it.

A few things to know:
- Week 1 is calibration. It may feel easy. That's intentional.
- If life gets in the way and you miss a day, skip it and move on. Don't double up.
- I can see your completed workouts in TP. I'm watching — in a good way.

If you have questions at any point, just reply to this email.

Let's get after it.

— Matt, Gravel God Cycling
gravelgodcycling.com
"""

    html_body = f"""
<div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
  <div style="background: #59473c; color: white; padding: 24px; border-radius: 4px 4px 0 0;">
    <h1 style="margin: 0; font-size: 22px;">Your plan is live</h1>
    {f'<p style="margin: 6px 0 0; opacity: 0.9; font-size: 15px;">{race_name}</p>' if race_name else ''}
  </div>

  <div style="background: #f9f9f7; padding: 24px; border: 1px solid #e0e0e0; border-top: none;">
    <p style="font-size: 15px; line-height: 1.6;">Hey {first_name},</p>

    <p style="font-size: 15px; line-height: 1.6;">Your custom training plan{race_mention} is built, reviewed, and <strong>live on TrainingPeaks</strong>.</p>

    <h3 style="margin: 24px 0 12px; font-size: 16px; color: #59473c;">Get started</h3>
    <ol style="font-size: 14px; padding-left: 20px; line-height: 2.2;">
      <li><strong>Log in to TrainingPeaks</strong> — you should have a coach invite from me. Accept it.</li>
      <li><strong>Check your calendar</strong> — every workout is loaded, day by day, through race week.</li>
      <li><strong>Follow the structure</strong> — each workout has target power zones, duration, and intervals.</li>
      <li><strong>Do today's workout.</strong> Don't overthink it.</li>
    </ol>

    <div style="margin: 24px 0; padding: 16px; background: #fff; border-left: 3px solid #59473c;">
      <p style="margin: 0 0 8px; font-size: 14px; color: #555;"><strong>Good to know:</strong></p>
      <ul style="font-size: 14px; padding-left: 18px; line-height: 1.8; color: #555; margin: 0;">
        <li>Week 1 is calibration. It may feel easy. That's intentional.</li>
        <li>If life gets in the way, skip the day and move on. Don't double up.</li>
        <li>I can see your completed workouts in TP. I'm watching — in a good way.</li>
      </ul>
    </div>

    <p style="font-size: 14px; line-height: 1.6;">Questions at any point? Just reply to this email.</p>

    <p style="font-size: 15px; line-height: 1.6; margin-top: 20px;">Let's get after it.</p>

    <p style="font-size: 14px; margin-top: 24px; color: #666;">— Matt, Gravel God Cycling<br>
    <a href="https://gravelgodcycling.com" style="color: #1A8A82;">gravelgodcycling.com</a></p>
  </div>
</div>"""

    ok = _send_email(customer_email, subject, text_body, html=html_body,
                     reply_to=NOTIFICATION_EMAIL)
    if ok:
        logger.info(f"Sent plan confirmation to {_mask_email(customer_email)} for {norm_id}")
        return jsonify({
            'status': 'confirmed',
            'athlete_id': norm_id,
            'email': _mask_email(customer_email),
        })
    else:
        return jsonify({'error': 'Failed to send confirmation email'}), 502


@app.route('/api/create-checkout', methods=['POST', 'OPTIONS'])
@limiter.limit("20/minute")
def create_checkout():
    """Create a Stripe Checkout Session from questionnaire data.

    Receives the full questionnaire submission, stores it temporarily,
    creates a Stripe Checkout Session, and returns the checkout URL.
    The customer completes payment on Stripe's hosted page, then the
    webhook handler loads the stored data to build the profile.
    """
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return '', 204

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400

    # Validate required fields
    email = (data.get('email') or '').strip().lower()
    if not email or '@' not in email or '.' not in email:
        return jsonify({'error': 'Valid email is required'}), 400

    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400

    # Validate at least one race
    races = data.get('races', [])
    if not races:
        return jsonify({'error': 'At least one race is required'}), 400

    # Compute price from A-race date
    a_race = next((r for r in races if r.get('priority') == 'A'), races[0])
    race_date_str = a_race.get('date', '')
    if not race_date_str:
        return jsonify({'error': 'A-race date is required'}), 400

    # Reject race dates more than 7 days in the past
    try:
        parsed_race_date = datetime.strptime(race_date_str, '%Y-%m-%d').date()
        if (date.today() - parsed_race_date).days > 7:
            return jsonify({'error': 'Race date cannot be more than 7 days in the past'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid race date format (expected YYYY-MM-DD)'}), 400

    pricing = compute_plan_price(race_date_str)

    # Generate intake ID and store questionnaire data
    intake_id = str(uuid.uuid4())
    data['computed_price_cents'] = pricing['price_cents']
    data['computed_weeks'] = pricing['weeks']
    store_intake(intake_id, data)

    # Look up pre-built price ID, capping at 17 for 17+ weeks
    price_key = min(pricing['weeks'], 17)
    price_id = TRAINING_PLAN_PRICE_IDS.get(price_key)

    # Create Stripe Checkout Session
    try:
        line_items = [{'price': price_id, 'quantity': 1}] if price_id else [{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': STRIPE_PRODUCT_NAME,
                    'description': f"{pricing['weeks']}-week custom training plan",
                },
                'unit_amount': pricing['price_cents'],
            },
            'quantity': 1,
        }]

        expires_at = int((datetime.now() + timedelta(minutes=CHECKOUT_EXPIRY_MINUTES)).timestamp())

        session_kwargs = dict(
            line_items=line_items,
            mode='payment',
            customer_email=email,
            customer_creation='always',
            client_reference_id=intake_id,
            metadata={
                'intake_id': intake_id,
                'product_type': 'training_plan',
                'tier': 'custom',
                'athlete_name': name,
                'weeks': str(pricing['weeks']),
                'price_cents': str(pricing['price_cents']),
            },
            success_url='https://gravelgodcycling.com/training-plans/success/?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://gravelgodcycling.com/training-plans/questionnaire/',
            expires_at=expires_at,
            after_expiration={
                'recovery': {
                    'enabled': True,
                    'allow_promotion_codes': True,
                }
            },
            # consent_collection removed — requires Stripe Checkout ToS acceptance
            # in dashboard.stripe.com/settings/checkout. Re-enable after accepting.
        )
        if ENABLE_AUTOMATIC_TAX:
            session_kwargs['automatic_tax'] = {'enabled': True}

        checkout_session = stripe.checkout.Session.create(**session_kwargs)

        logger.info(f"Created checkout session {checkout_session.id} for intake {intake_id} "
                     f"({pricing['weeks']}wk, {pricing['price_display']}, {_mask_email(email)})")

        return jsonify({
            'checkout_url': checkout_session.url,
            'intake_id': intake_id,
            'price': pricing,
        })

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating checkout: {e}")
        return jsonify({'error': 'Payment service error. Please try again.'}), 502
    except Exception as e:
        logger.exception(f"Checkout creation error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/create-coaching-checkout', methods=['POST', 'OPTIONS'])
@limiter.limit("20/minute")
def create_coaching_checkout():
    """Create a Stripe Checkout Session for coaching subscription.

    Expects JSON: {email, name, tier: "min"|"mid"|"max"}
    Returns: {checkout_url}
    """
    if request.method == 'OPTIONS':
        return '', 204

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400

    email = (data.get('email') or '').strip().lower()
    if not email or '@' not in email or '.' not in email:
        return jsonify({'error': 'Valid email is required'}), 400

    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400

    tier = (data.get('tier') or '').strip().lower()
    if tier not in COACHING_PRICE_IDS:
        return jsonify({'error': f'Invalid tier: {tier}. Must be min, mid, or max'}), 400

    price_id = COACHING_PRICE_IDS[tier]

    try:
        expires_at = int((datetime.now() + timedelta(minutes=CHECKOUT_EXPIRY_MINUTES)).timestamp())

        # Line items: recurring subscription + one-time $99 setup fee
        line_items = [
            {'price': price_id, 'quantity': 1},
        ]
        if COACHING_SETUP_FEE_PRICE_ID:
            line_items.append({'price': COACHING_SETUP_FEE_PRICE_ID, 'quantity': 1})

        session_kwargs = dict(
            line_items=line_items,
            mode='subscription',
            customer_email=email,
            allow_promotion_codes=True,
            phone_number_collection={'enabled': True},
            metadata={
                'product_type': 'coaching',
                'tier': tier,
                'athlete_name': name,
            },
            subscription_data={
                'metadata': {
                    'tier': tier,
                    'athlete_name': name,
                },
            },
            success_url='https://gravelgodcycling.com/coaching/welcome/?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://gravelgodcycling.com/coaching/',
            expires_at=expires_at,
            after_expiration={
                'recovery': {
                    'enabled': True,
                    'allow_promotion_codes': True,
                }
            },
            # consent_collection removed — requires Stripe Checkout ToS acceptance
            # in dashboard.stripe.com/settings/checkout. Re-enable after accepting.
        )
        if ENABLE_AUTOMATIC_TAX:
            session_kwargs['automatic_tax'] = {'enabled': True}

        checkout_session = stripe.checkout.Session.create(**session_kwargs)

        logger.info(f"Created coaching checkout {checkout_session.id} "
                     f"(tier={tier}, setup_fee=$99, {_mask_email(email)})")

        return jsonify({'checkout_url': checkout_session.url})

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating coaching checkout: {e}")
        return jsonify({'error': 'Payment service error. Please try again.'}), 502
    except Exception as e:
        logger.exception(f"Coaching checkout error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/create-consulting-checkout', methods=['POST', 'OPTIONS'])
@limiter.limit("20/minute")
def create_consulting_checkout():
    """Create a Stripe Checkout Session for consulting.

    Expects JSON: {email, name, hours: 1}
    Returns: {checkout_url}
    """
    if request.method == 'OPTIONS':
        return '', 204

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400

    email = (data.get('email') or '').strip().lower()
    if not email or '@' not in email or '.' not in email:
        return jsonify({'error': 'Valid email is required'}), 400

    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400

    hours = data.get('hours', 1)
    try:
        hours = int(hours)
        if hours < 1 or hours > 10:
            return jsonify({'error': 'Hours must be between 1 and 10'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid hours value'}), 400

    try:
        expires_at = int((datetime.now() + timedelta(minutes=CHECKOUT_EXPIRY_MINUTES)).timestamp())

        session_kwargs = dict(
            line_items=[{'price': CONSULTING_PRICE_ID, 'quantity': hours}],
            mode='payment',
            customer_email=email,
            customer_creation='always',
            metadata={
                'product_type': 'consulting',
                'athlete_name': name,
                'hours': str(hours),
            },
            success_url='https://gravelgodcycling.com/consulting/confirmed/?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://gravelgodcycling.com/consulting/',
            expires_at=expires_at,
            after_expiration={
                'recovery': {
                    'enabled': True,
                    'allow_promotion_codes': True,
                }
            },
            # consent_collection removed — requires Stripe Checkout ToS acceptance
            # in dashboard.stripe.com/settings/checkout. Re-enable after accepting.
        )
        if ENABLE_AUTOMATIC_TAX:
            session_kwargs['automatic_tax'] = {'enabled': True}

        checkout_session = stripe.checkout.Session.create(**session_kwargs)

        logger.info(f"Created consulting checkout {checkout_session.id} "
                     f"({hours}hr, {_mask_email(email)})")

        return jsonify({'checkout_url': checkout_session.url})

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating consulting checkout: {e}")
        return jsonify({'error': 'Payment service error. Please try again.'}), 502
    except Exception as e:
        logger.exception(f"Consulting checkout error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/webhook/woocommerce', methods=['POST'])
def woocommerce_webhook():
    """Handle WooCommerce order webhook."""
    signature = request.headers.get('X-WC-Webhook-Signature', '')

    if not verify_woocommerce_signature(request.data, signature):
        logger.warning("Invalid WooCommerce signature")
        return jsonify({'error': 'Invalid signature'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400

    # Only process completed orders
    if data.get('status') not in ['completed', 'processing']:
        return jsonify({'status': 'ignored', 'reason': 'Order not completed'})

    try:
        order_data = extract_woocommerce_data(data)

        # Idempotency check
        if check_idempotency(order_data['order_id']):
            return jsonify({
                'status': 'duplicate',
                'message': 'Order already processed'
            })

        # Validate order data
        is_valid, error_msg = validate_order_data(order_data)
        if not is_valid:
            logger.error(f"Invalid order data: {error_msg}")
            return jsonify({'error': error_msg}), 400

        athlete_id, profile_path = create_athlete_profile(order_data)

        # Mark as processed BEFORE pipeline to prevent TOCTOU race with
        # webhook retries. Stripe/WooCommerce retry if we don't respond within
        # ~20s, and the pipeline takes up to 5 minutes. Without this, retries
        # pass the idempotency check and start duplicate pipelines.
        mark_order_processed(order_data['order_id'], athlete_id)

        result = run_pipeline(athlete_id, deliver=True)
        log_order(order_data, result)

        if result['success']:
            try:
                persist_deliverables(athlete_id)
            except Exception as e:
                logger.error(f"Failed to persist deliverables for {athlete_id}: {e}")

        details = _build_plan_notification_details(order_data, result)
        if result['success']:
            details['download_token'] = _generate_download_token(athlete_id)
            _notify_new_order('training_plan', details)
            return jsonify({
                'status': 'success',
                'athlete_id': athlete_id,
                'message': 'Training plan generated and delivered'
            })
        else:
            _notify_new_order('training_plan_FAILED', details)
            return jsonify({
                'status': 'pipeline_failed',
                'athlete_id': athlete_id,
                'message': 'Order received but pipeline failed. Manual intervention required.'
            })

    except Exception as e:
        logger.exception(f"WooCommerce webhook error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/webhook/stripe', methods=['POST'])
@limiter.limit("60/minute")
def stripe_webhook():
    """Handle Stripe webhook events (completed + expired checkouts)."""
    signature = request.headers.get('Stripe-Signature', '')

    if not verify_stripe_signature(request.data, signature):
        logger.warning("Invalid Stripe signature")
        return jsonify({'error': 'Invalid signature'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400

    event_type = data.get('type', '')

    # Route by event type
    if event_type == 'checkout.session.expired':
        return _handle_checkout_expired(data)
    elif event_type != 'checkout.session.completed':
        return jsonify({'status': 'ignored', 'reason': f'Event type: {event_type}'})

    try:
        session = data.get('data', {}).get('object', {})
        metadata = session.get('metadata', {})
        product_type = metadata.get('product_type', 'training_plan')
        order_id = session.get('id', '')

        # Check if this was a recovered session
        recovered_from = session.get('recovered_from')
        if recovered_from:
            logger.info(f"Recovered checkout from expired session {recovered_from}")

        # Idempotency check (applies to all product types)
        if check_idempotency(order_id):
            return jsonify({
                'status': 'duplicate',
                'message': 'Order already processed'
            })

        # Route by product type
        if product_type == 'coaching':
            return _handle_coaching_webhook(session, metadata, order_id)
        elif product_type == 'consulting':
            return _handle_consulting_webhook(session, metadata, order_id)
        else:
            return _handle_training_plan_webhook(data, order_id)

    except Exception as e:
        logger.exception(f"Stripe webhook error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


def _handle_checkout_expired(data: dict):
    """Handle expired checkout session — send recovery email if customer opted in.

    Includes idempotency to prevent duplicate recovery emails when Stripe retries.
    Returns 200 on all paths (even errors) to prevent Stripe from retrying.
    """
    try:
        session = data.get('data', {}).get('object', {})
        session_id = session.get('id', '')

        # Idempotency — prevent duplicate recovery emails on Stripe retry
        expired_key = f'expired_{session_id}'
        if check_idempotency(expired_key):
            return jsonify({'status': 'duplicate', 'message': 'Expired session already handled'})

        # Mark early to prevent duplicates from concurrent retries
        mark_order_processed(expired_key, 'recovery')

        email = session.get('customer_details', {}).get('email', '')
        metadata = session.get('metadata', {})
        product_type = metadata.get('product_type', 'training_plan')
        athlete_name = metadata.get('athlete_name', '')
        consent = session.get('consent', {})

        # Stripe provides a recovery URL when after_expiration.recovery is enabled
        recovery = session.get('after_expiration', {}).get('recovery', {})
        recovery_url = recovery.get('url', '')

        if not email or not recovery_url:
            logger.info(f"Expired checkout {session_id} — no email or recovery URL")
            return jsonify({'status': 'ignored', 'reason': 'No recovery possible'})

        # Only send if customer opted in to promotional emails
        if consent.get('promotions') != 'opt_in':
            logger.info(f"Expired checkout — customer did not opt in ({_mask_email(email)})")
            return jsonify({'status': 'ignored', 'reason': 'No promotional consent'})

        # Build product-specific recovery email
        _send_recovery_email(email, athlete_name, product_type, metadata, recovery_url)

        _log_product_event('cart_recovery', session_id,
                           email=email, original_product=product_type,
                           recovery_url_sent=True)

        logger.info(f"Sent recovery email for {product_type} to {_mask_email(email)}")
        return jsonify({'status': 'recovery_sent'})

    except Exception as e:
        logger.exception(f"Error handling expired checkout: {e}")
        # Return 200 even on error to prevent Stripe from retrying and
        # sending duplicate recovery emails. The idempotency mark is already
        # set, so retries would be caught, but 200 is cleaner.
        return jsonify({'status': 'error', 'message': 'Logged for manual review'})


def _send_recovery_email(email: str, name: str, product_type: str,
                         metadata: dict, recovery_url: str):
    """Send a recovery email for an abandoned checkout."""
    first_name = name.split()[0] if name else 'there'

    if product_type == 'training_plan':
        weeks = metadata.get('weeks', '')
        subject = f"Your {weeks}-week training plan is still waiting"
        body = (
            f"Hey {first_name},\n\n"
            f"You were building a custom {weeks}-week training plan — "
            f"looks like you didn't finish checking out.\n\n"
            f"Your plan details are saved. Pick up where you left off:\n"
            f"{recovery_url}\n\n"
            f"Your race is coming up. The sooner you start structured training, "
            f"the stronger you'll be on race day.\n\n"
            f"— Matt, Gravel God Cycling\n"
            f"gravelgodcycling.com"
        )
    elif product_type == 'coaching':
        tier = metadata.get('tier', '')
        subject = "Your coaching spot is still available"
        body = (
            f"Hey {first_name},\n\n"
            f"You were signing up for {tier}-tier coaching — "
            f"your spot is still open.\n\n"
            f"Pick up where you left off:\n"
            f"{recovery_url}\n\n"
            f"Athletes who work with a coach see measurable gains within "
            f"the first few weeks. Let's get started.\n\n"
            f"— Matt, Gravel God Cycling\n"
            f"gravelgodcycling.com"
        )
    else:  # consulting
        hours = metadata.get('hours', '1')
        subject = "Your consulting session is ready to book"
        body = (
            f"Hey {first_name},\n\n"
            f"You were booking a {hours}-hour consulting session — "
            f"still interested?\n\n"
            f"Complete your booking:\n"
            f"{recovery_url}\n\n"
            f"— Matt, Gravel God Cycling\n"
            f"gravelgodcycling.com"
        )

    reply_to = NOTIFICATION_EMAIL or None
    if RESEND_API_KEY:
        if not _send_email(email, subject, body, reply_to=reply_to):
            logger.critical(
                f"ABANDONED CART — email failed\n"
                f"  Email: {_mask_email(email)}\n  Product: {product_type}\n"
                f"  Recovery URL: {recovery_url}"
            )
        else:
            logger.info(f"Recovery email sent to {_mask_email(email)}")
    else:
        logger.critical(
            f"ABANDONED CART — Resend not configured, manual follow-up needed\n"
            f"  Email: {_mask_email(email)}\n  Name: {name}\n"
            f"  Product: {product_type}\n  Recovery URL: {recovery_url}"
        )


def _handle_training_plan_webhook(data: dict, order_id: str):
    """Handle training plan checkout completion — create profile + run pipeline."""
    order_data = extract_stripe_data(data)

    is_valid, error_msg = validate_order_data(order_data)
    if not is_valid:
        logger.error(f"Invalid order data: {error_msg}")
        return jsonify({'error': error_msg}), 400

    athlete_id, profile_path = create_athlete_profile(order_data)

    # Load intake data for pipeline and backup
    intake_id = data.get('data', {}).get('object', {}).get('metadata', {}).get('intake_id', '')
    intake_data = load_intake(intake_id) if intake_id else {}
    if intake_data:
        backup_path = Path(ATHLETES_DIR) / athlete_id / 'intake_backup.json'
        try:
            with open(backup_path, 'w') as f:
                json.dump(intake_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to backup intake data: {e}")

    # Mark BEFORE pipeline — see WooCommerce handler comment for rationale
    mark_order_processed(order_data['order_id'], athlete_id)

    # Send instant payment confirmation to customer (before pipeline runs)
    customer_email = order_data['profile'].get('email', '')
    customer_name = order_data['profile'].get('name', '')
    race_name = intake_data.get('race_name', '') if intake_data else ''
    _send_payment_confirmation(customer_email, customer_name, race_name=race_name)

    result = run_pipeline(athlete_id, deliver=True, intake_data=intake_data or None)
    log_order(order_data, result)

    if result['success']:
        try:
            persist_deliverables(athlete_id)
        except Exception as e:
            logger.error(f"Failed to persist deliverables for {athlete_id}: {e}")

    details = _build_plan_notification_details(order_data, result, intake_data)
    if result['success']:
        details['download_token'] = _generate_download_token(athlete_id)
        _notify_new_order('training_plan', details)
        return jsonify({
            'status': 'success',
            'athlete_id': athlete_id,
            'message': 'Training plan generated and delivered'
        })
    else:
        _notify_new_order('training_plan_FAILED', details)
        return jsonify({
            'status': 'pipeline_failed',
            'athlete_id': athlete_id,
            'message': 'Order received but pipeline failed. Manual intervention required.'
        })


def _handle_coaching_webhook(session: dict, metadata: dict, order_id: str):
    """Handle coaching subscription checkout completion — log + notify."""
    tier = metadata.get('tier', 'unknown')
    name = metadata.get('athlete_name', 'Unknown')
    email = session.get('customer_details', {}).get('email', '')
    subscription_id = session.get('subscription', '')

    logger.info(f"Coaching subscription started: {name} ({_mask_email(email)}), "
                f"tier={tier}, subscription={subscription_id}")

    mark_order_processed(order_id, sanitize_athlete_id(name))
    _log_product_event('coaching', order_id,
                       tier=tier, name=name, email=email,
                       subscription_id=subscription_id)
    _notify_new_order('coaching', {
        'name': name,
        'email': email,
        'tier': tier,
        'subscription_id': subscription_id,
        'order_id': order_id,
    })

    return jsonify({
        'status': 'success',
        'product_type': 'coaching',
        'tier': tier,
        'message': f'Coaching subscription ({tier}) started for {name}'
    })


def _handle_consulting_webhook(session: dict, metadata: dict, order_id: str):
    """Handle consulting checkout completion — log + notify."""
    name = metadata.get('athlete_name', 'Unknown')
    hours = metadata.get('hours', '1')
    email = session.get('customer_details', {}).get('email', '')

    logger.info(f"Consulting booked: {name} ({_mask_email(email)}), {hours}hr")

    mark_order_processed(order_id, sanitize_athlete_id(name))
    _log_product_event('consulting', order_id,
                       name=name, email=email, hours=hours)
    _notify_new_order('consulting', {
        'name': name,
        'email': email,
        'hours': hours,
        'order_id': order_id,
    })

    return jsonify({
        'status': 'success',
        'product_type': 'consulting',
        'hours': hours,
        'message': f'Consulting ({hours}hr) booked for {name}'
    })


# =============================================================================
# TEST ENDPOINT — runs the EXACT same code path as a real Stripe webhook.
# Secured by CRON_SECRET header. Requires intake_id with stored questionnaire.
# =============================================================================
@app.route('/webhook/test', methods=['POST'])
def test_webhook():
    """Simulate a real customer checkout → pipeline → notification flow.

    Runs the identical code path as _handle_training_plan_webhook:
    extract → validate → create profile → load intake → mark processed →
    run pipeline → log order → send notification email.

    Required: intake_id (from a stored questionnaire), name, email.
    """
    secret = request.headers.get('X-Cron-Secret', '')
    if not secret or not hmac.compare_digest(secret, os.environ.get('CRON_SECRET', '')):
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json() or {}
    intake_id = data.get('intake_id', '')

    # If questionnaire data is provided inline, store it and generate an intake_id
    if not intake_id and data.get('questionnaire'):
        intake_id = str(uuid.uuid4())
        store_intake(intake_id, data['questionnaire'])
        logger.info(f"Test: stored inline questionnaire as {intake_id}")

    if not intake_id:
        return jsonify({'error': 'intake_id or questionnaire object is required'}), 400

    # Build a fake Stripe event that mirrors real checkout.session.completed
    order_id = 'test_' + datetime.now().strftime('%Y%m%d%H%M%S')
    fake_stripe_data = {
        'data': {
            'object': {
                'id': order_id,
                'metadata': {
                    'intake_id': intake_id,
                    'product_type': 'training_plan',
                    'tier': 'custom',
                    'athlete_name': data.get('name', 'Test Athlete'),
                },
                'customer_details': {
                    'email': data.get('email', 'test@example.com'),
                    'name': data.get('name', 'Test Athlete'),
                }
            }
        }
    }

    # === Same code path as _handle_training_plan_webhook ===

    order_data = extract_stripe_data(fake_stripe_data)

    is_valid, error_msg = validate_order_data(order_data)
    if not is_valid:
        return jsonify({'error': error_msg}), 400

    athlete_id, profile_path = create_athlete_profile(order_data)

    # Load intake data (questionnaire) for pipeline
    intake_data = load_intake(intake_id)
    if not intake_data:
        return jsonify({'error': f'Intake {intake_id} not found or expired'}), 404

    # Backup intake (same as real flow)
    backup_path = Path(ATHLETES_DIR) / athlete_id / 'intake_backup.json'
    try:
        with open(backup_path, 'w') as f:
            json.dump(intake_data, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to backup intake data: {e}")

    # Idempotency mark (same as real flow)
    mark_order_processed(order_data['order_id'], athlete_id)

    # Send instant payment confirmation to customer (same as real flow)
    customer_email = order_data['profile'].get('email', '')
    customer_name = order_data['profile'].get('name', '')
    race_name = intake_data.get('race_name', '') if intake_data else ''
    _send_payment_confirmation(customer_email, customer_name, race_name=race_name)

    # Run pipeline with deliver=True (same as real flow)
    result = run_pipeline(athlete_id, deliver=True, intake_data=intake_data)

    # Log order (same as real flow)
    log_order(order_data, result)

    # Persist deliverables to volume + create zip (same as real flow)
    if result['success']:
        try:
            persist_deliverables(athlete_id)
        except Exception as e:
            logger.error(f"Failed to persist deliverables for {athlete_id}: {e}")

    # Send notification email (same as real flow)
    details = _build_plan_notification_details(order_data, result, intake_data)
    if result['success']:
        details['download_token'] = _generate_download_token(athlete_id)
        _notify_new_order('training_plan', details)
        return jsonify({
            'status': 'success',
            'athlete_id': athlete_id,
            'profile_path': str(profile_path),
            'message': 'Full flow complete: profile → pipeline → log → notification',
            'pipeline': result,
        })
    else:
        _notify_new_order('training_plan_FAILED', details)
        return jsonify({
            'status': 'pipeline_failed',
            'athlete_id': athlete_id,
            'profile_path': str(profile_path),
            'message': 'Pipeline failed. Notification sent.',
            'pipeline': result,
        })


# =============================================================================
# POST-PURCHASE FOLLOW-UP EMAIL SEQUENCE
# =============================================================================

# Day offsets and email templates for training plan follow-ups.
# Coaching and consulting follow-ups are manual (high-touch).
FOLLOWUP_SEQUENCE = [
    {
        'day': 1,
        'subject': 'Getting started with your training plan',
        'template': (
            "Hey {first_name},\n\n"
            "Your training plan was delivered yesterday. Here's how to get "
            "the most out of it:\n\n"
            "1. Import the .zwo files into TrainingPeaks, Zwift, or Wahoo\n"
            "2. Read the training guide — especially the phase overview\n"
            "3. Do today's workout. Don't overthink it.\n\n"
            "Week 1 is calibration. The workouts might feel easy. That's "
            "intentional. Trust the process.\n\n"
            "If you have questions, reply to this email.\n\n"
            "— Matt, Gravel God Cycling\n"
            "gravelgodcycling.com"
        ),
    },
    {
        'day': 3,
        'subject': 'Quick check-in — how\'s week 1?',
        'template': (
            "Hey {first_name},\n\n"
            "You're a few days into your plan. A couple things:\n\n"
            "- If your FTP was estimated, the zones might feel off. That's "
            "normal. Week 1 includes a test protocol to dial it in.\n"
            "- If you missed a workout, don't double up. Just pick up where "
            "the plan says to go next.\n"
            "- The strength sessions are optional but they matter. Even 20 "
            "minutes twice a week makes a difference by race day.\n\n"
            "Your free race prep kit has packing lists, race-day checklists, "
            "and course intel for your target event:\n"
            "https://gravelgodcycling.com/gravel-races/\n\n"
            "— Matt\n"
            "gravelgodcycling.com"
        ),
    },
    {
        'day': 7,
        'subject': 'Week 1 done — what to expect next',
        'template': (
            "Hey {first_name},\n\n"
            "You've finished your first week. The real training starts now.\n\n"
            "Week 2+ is where the workouts start building. The efforts get "
            "harder, the long rides get longer, and the plan starts earning "
            "its keep.\n\n"
            "Two things that matter most from here:\n"
            "1. Consistency > intensity. Showing up 5 days matters more than "
            "one hero session.\n"
            "2. Sleep and fueling are training. The plan assumes you're "
            "recovering between sessions.\n\n"
            "If you want a human in your corner — weekly adjustments, "
            "race-day strategy, and real accountability — coaching starts at "
            "$199 every 4 weeks:\n"
            "https://gravelgodcycling.com/coaching/\n\n"
            "Train hard.\n\n"
            "— Matt\n"
            "gravelgodcycling.com"
        ),
    },
]


def _get_followup_log_path():
    """Path to the follow-up sent log."""
    log_dir = Path(DATA_DIR) / '.logs'
    log_dir.mkdir(exist_ok=True)
    return log_dir / 'followup_sent.jsonl'


def _get_sent_followups():
    """Load set of (order_id, day) tuples already sent."""
    sent = set()
    log_path = _get_followup_log_path()
    if log_path.exists():
        for line in log_path.read_text().strip().split('\n'):
            if not line:
                continue
            try:
                entry = json.loads(line)
                sent.add((entry['order_id'], entry['day']))
            except (json.JSONDecodeError, KeyError):
                continue
    return sent


def _mark_followup_sent(order_id: str, day: int, email: str):
    """Record that a follow-up was sent."""
    log_path = _get_followup_log_path()
    entry = json.dumps({
        'order_id': order_id,
        'day': day,
        'email': _mask_email(email),
        'sent_at': datetime.utcnow().isoformat(),
    })
    with open(log_path, 'a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(entry + '\n')
        fcntl.flock(f, fcntl.LOCK_UN)


def _send_followup_email(email: str, subject: str, body: str):
    """Send a follow-up email via Resend. Returns True on success."""
    if not RESEND_API_KEY:
        logger.warning(f"Resend not configured — skipping followup to {_mask_email(email)}")
        return False

    reply_to = NOTIFICATION_EMAIL or None
    return _send_email(email, subject, body, reply_to=reply_to)


def process_followup_emails():
    """Check order logs and send due follow-up emails. Returns stats dict.

    Reads from YYYY-MM.jsonl files (written by log_order and _log_product_event).
    Only processes training_plan orders that succeeded.
    """
    log_dir = Path(DATA_DIR) / '.logs'

    if not log_dir.exists():
        return {'checked': 0, 'sent': 0, 'skipped': 0, 'errors': 0}

    sent_followups = _get_sent_followups()
    now = datetime.utcnow()
    stats = {'checked': 0, 'sent': 0, 'skipped': 0, 'errors': 0}

    # Read from all YYYY-MM.jsonl files (the format log_order actually writes to)
    for log_file in sorted(log_dir.glob('20*.jsonl')):
        for line in log_file.read_text().strip().split('\n'):
            if not line:
                continue
            try:
                order = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Only follow up on training_plan orders (coaching/consulting are high-touch)
            if order.get('product_type') != 'training_plan':
                continue

            # Skip failed orders — no plan was delivered
            if not order.get('success', True):
                continue

            stats['checked'] += 1
            order_id = order.get('order_id', '')
            email = order.get('email', '')
            name = order.get('name', order.get('customer_name', ''))
            order_time = order.get('timestamp', order.get('processed_at', ''))

            if not email or not order_time or not order_id:
                continue

            try:
                order_dt = datetime.fromisoformat(order_time.replace('Z', '+00:00').replace('+00:00', ''))
            except (ValueError, AttributeError):
                continue

            days_since = (now - order_dt).days

            for followup in FOLLOWUP_SEQUENCE:
                day = followup['day']
                # Send on the target day or up to 2 days late (catch-up window)
                if days_since < day or days_since > day + 2:
                    continue
                if (order_id, day) in sent_followups:
                    continue

                first_name = name.split()[0] if name else 'there'
                body = followup['template'].format(first_name=first_name)
                subject = followup['subject']

                if _send_followup_email(email, subject, body):
                    _mark_followup_sent(order_id, day, email)
                    sent_followups.add((order_id, day))
                    stats['sent'] += 1
                    logger.info(
                        f"Followup day {day} sent to {_mask_email(email)} "
                        f"(order {order_id})"
                    )
                else:
                    stats['errors'] += 1

    stats['skipped'] = stats['checked'] * len(FOLLOWUP_SEQUENCE) - stats['sent'] - stats['errors']
    return stats


@app.route('/api/cron/followup-emails', methods=['POST'])
@limiter.limit("5/minute")
def cron_followup_emails():
    """Daily cron endpoint — send follow-up emails for recent orders.

    Secured by CRON_SECRET header. Call daily from an external scheduler.
    """
    secret = request.headers.get('X-Cron-Secret', '')
    if not CRON_SECRET:
        return jsonify({'error': 'CRON_SECRET not configured'}), 503
    if not hmac.compare_digest(secret, CRON_SECRET):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        stats = process_followup_emails()
        logger.info(f"Follow-up cron complete: {stats}")
        return jsonify({'status': 'ok', **stats})
    except Exception as e:
        logger.exception(f"Follow-up cron error: {e}")
        return jsonify({'error': 'Internal error'}), 500


# =============================================================================
# STARTUP
# =============================================================================

# Clean up stale intake files on startup
try:
    cleanup_stale_intakes()
except Exception as e:
    logger.warning(f"Intake cleanup on startup failed: {e}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
