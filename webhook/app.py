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
import threading
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

# CORS — only allow requests from our brand sites
ALLOWED_ORIGINS = [
    'https://gravelgodcycling.com', 'https://www.gravelgodcycling.com',
    'https://roadielabs.com', 'https://www.roadielabs.com',
]

# Multi-brand support — this webhook serves all brand sites. Brand is derived
# from the request Origin at checkout creation, stored in Stripe metadata,
# and read back in the webhook handlers (success URLs, GA4 routing, emails).
BRANDS = {
    'gravelgod': {
        'name': 'Gravel God Cycling',
        'site': 'https://gravelgodcycling.com',
        'questionnaire_path': '/training-plans/questionnaire/',
        'ga4_measurement_id': os.environ.get('GA4_MEASUREMENT_ID', 'G-EJJZ9T6M52'),
        'ga4_mp_api_secret': os.environ.get('GA4_MP_API_SECRET', ''),
    },
    'roadielabs': {
        'name': 'Roadie Labs',
        'site': 'https://roadielabs.com',
        'questionnaire_path': '/questionnaire/',
        'ga4_measurement_id': os.environ.get('GA4_MEASUREMENT_ID_RL', ''),
        'ga4_mp_api_secret': os.environ.get('GA4_MP_API_SECRET_RL', ''),
    },
}
DEFAULT_BRAND = 'gravelgod'


def _brand_from_origin(origin: str) -> str:
    """Map a request Origin header to a brand key."""
    if 'roadielabs.com' in (origin or '').lower():
        return 'roadielabs'
    return DEFAULT_BRAND


def _brand_config(brand: str) -> dict:
    return BRANDS.get(brand or DEFAULT_BRAND, BRANDS[DEFAULT_BRAND])

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

# Pipeline timeout. Must stay BELOW gunicorn's --timeout (600 in Dockerfile)
# so the timeout path can still send the FAILED notification email before
# gunicorn kills the worker.
PIPELINE_TIMEOUT = int(os.environ.get('PIPELINE_TIMEOUT', '480'))


def _pipeline_error_excerpt(result: dict, limit: int = 500) -> str:
    """Best error excerpt from a pipeline result.

    intake_to_plan.py reports most failures on stdout (stderr is often
    empty), so fall back to the TAIL of stdout — that's where the
    error/traceback lands.
    """
    stderr = (result.get('stderr') or '').strip()
    if stderr:
        return stderr[:limit]
    stdout = (result.get('stdout') or '').strip()
    return stdout[-limit:] if stdout else ''

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
    """Hourly housekeeping: stale intakes + orphaned pipeline jobs."""
    global _last_intake_cleanup
    now = datetime.now()
    if (now - _last_intake_cleanup).total_seconds() > 3600:
        _last_intake_cleanup = now
        try:
            cleanup_stale_intakes()
        except Exception as e:
            logger.warning(f"Periodic intake cleanup failed: {e}")
        try:
            stats = sweep_stuck_jobs()
            if stats.get('retried') or stats.get('failed'):
                logger.warning(f"Periodic job sweep: {stats}")
        except Exception as e:
            logger.error(f"Periodic job sweep failed: {e}")


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


def _send_email(to: str, subject: str, body: str, html: str = None, reply_to: str = None,
                attachments: list = None):
    """Send email via Resend HTTP API. Returns True on success.

    attachments: list of (filename, path) tuples; files are base64-encoded.
    Resend caps total message size at 40MB.
    """
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
    if attachments:
        import base64
        encoded = []
        for fname, fpath in attachments:
            try:
                encoded.append({
                    'filename': fname,
                    'content': base64.b64encode(Path(fpath).read_bytes()).decode(),
                })
            except Exception as e:
                logger.warning(f"Skipping attachment {fname}: {e}")
        if encoded:
            payload['attachments'] = encoded

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

    # Edge-case review flags — profiles where automation is most likely to
    # need a human eye before delivery. The plan still generated and passed
    # the compliance gate; these flag elevated-judgment cases.
    review_flags = []
    try:
        _hours_num = float(str(hours).split('-')[0]) if hours else 0
    except (ValueError, TypeError):
        _hours_num = 0
    if _hours_num and _hours_num < 6:
        review_flags.append('Very low hours (<6h/wk) — check workout fit')
    try:
        _weeks_num = int(weeks) if weeks else 0
    except (ValueError, TypeError):
        _weeks_num = 0
    if _weeks_num > 26:
        review_flags.append(f'Long plan ({_weeks_num} wks) — check phase balance')
    _age = details.get('age', 0)
    try:
        _age = int(_age)
    except (ValueError, TypeError):
        _age = 0
    if _age >= 55:
        review_flags.append(f'Masters athlete ({_age}) — check recovery spacing')
    if details.get('risk_factors'):
        review_flags.append(
            'Risk factors: ' + ', '.join(str(r) for r in details['risk_factors']))

    # Strongest flag: the plan DELIVERED but an automatic compliance check
    # failed. The order is NOT lost — it just needs a human pass before sending.
    needs_review = bool(details.get('needs_review'))
    if needs_review:
        review_flags.insert(0,
            'AUTO-CHECK FAILED — plan delivered but a compliance rule was '
            'flagged. Review coaching_brief.md and adjust before sending.')

    subject = f"[GG] {'New order' if pipeline_ok else 'FAILED'}: {name} — {race_name or 'training plan'}"
    if pipeline_ok and needs_review:
        subject = subject.replace('[GG] New order', '[GG] ⚠ NEEDS REVIEW')
    elif pipeline_ok and review_flags:
        subject = subject.replace('[GG] New order', '[GG] New order ⚠ REVIEW')

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

    {'<div style="margin: 16px 0; padding: 12px 16px; background: #fff3cd; border: 2px solid #B7950B; border-radius: 4px;"><strong style="color: #59473c;">⚠ REVIEW FLAGS</strong><ul style="margin: 8px 0 0; padding-left: 20px; font-size: 13px;">' + ''.join('<li>' + f + '</li>' for f in review_flags) + '</ul></div>' if review_flags else ''}

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


def _send_ga4_purchase(order_id: str, value_cents, product_type: str,
                       item_name: str, brand: str = DEFAULT_BRAND):
    """Record a purchase in GA4 via Measurement Protocol (server-side).

    Fires for every real payment regardless of the buyer's cookie-consent
    state — the client-side purchase event (success page) only records when
    the visitor accepted the cookie banner (verified Jun 2026, invisible
    even in Realtime otherwise). Shares transaction_id with the client-side
    event so GA4 deduplicates the two. Routes to the brand's GA4 property.
    Never raises — analytics must not affect order processing. No-op until
    the brand's MP api_secret env var is set; skips test orders.
    """
    cfg = _brand_config(brand)
    if not cfg['ga4_mp_api_secret'] or not cfg['ga4_measurement_id']:
        return
    if order_id.startswith('test_'):
        return
    try:
        payload = {
            # Synthetic client_id — server event with no browser context.
            # Deterministic per order so Stripe retries map to one "user".
            'client_id': f'srv.{order_id[-16:] or "order"}',
            'events': [{
                'name': 'purchase',
                'params': {
                    'transaction_id': order_id,
                    'currency': 'USD',
                    'value': round((value_cents or 0) / 100, 2),
                    'product_type': product_type,
                    'event_source': 'stripe_webhook',
                    'items': [{
                        'item_name': item_name,
                        'item_category': product_type,
                        'price': round((value_cents or 0) / 100, 2),
                        'quantity': 1,
                    }],
                },
            }],
        }
        resp = http_requests.post(
            'https://www.google-analytics.com/mp/collect',
            params={'measurement_id': cfg['ga4_measurement_id'],
                    'api_secret': cfg['ga4_mp_api_secret']},
            json=payload,
            timeout=5,
        )
        if resp.status_code >= 300:
            logger.warning(f"GA4 MP purchase non-2xx: {resp.status_code}")
        else:
            logger.info(f"GA4 purchase recorded: {product_type} "
                        f"${(value_cents or 0) / 100:.2f} ({order_id[:24]})")
    except Exception as e:
        logger.warning(f"GA4 MP purchase failed (non-fatal): {e}")


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
                               race_name: str = '', plan_weeks: str = '',
                               brand: str = DEFAULT_BRAND):
    """Send immediate payment confirmation to customer.

    Auto-fires on successful Stripe checkout. Tells them what they bought,
    that we're building their plan, and when to expect it. Sign-off and
    site link follow the brand the customer bought from.
    """
    if not RESEND_API_KEY:
        logger.warning("Cannot send payment confirmation — RESEND_API_KEY not set")
        return

    brand_cfg = _brand_config(brand)
    brand_name = brand_cfg['name']
    brand_site = brand_cfg['site'].replace('https://', '')

    first_name = customer_name.split()[0] if customer_name else 'there'
    race_mention = f' for {race_name}' if race_name else ''
    weeks_mention = f'{plan_weeks}-week ' if plan_weeks else ''

    subject = f'Payment confirmed — your {weeks_mention}training plan{race_mention}'

    tp_connect_url = 'https://home.trainingpeaks.com/attachtocoach?sharedKey=2OTEPC6BXNVQU'

    text = f"""Hey {first_name},

Payment received — thank you.

YOUR ONE ACTION ITEM:
Connect to my coaching account on TrainingPeaks so I can push your workouts there:
{tp_connect_url}

If you don't have a TrainingPeaks account, create a free one first at trainingpeaks.com, then click the link above.

WHAT HAPPENS NEXT:
1. Your custom {weeks_mention}training plan{race_mention} is being built right now.
2. I'll review it personally and make sure everything is dialed.
3. Within 24 hours, your workouts will be live on your TrainingPeaks calendar.
4. You'll get an email when it's ready with your training guide (PDF).

Questions? Reply to this email.

— Matti, {brand_name}
{brand_site}
"""

    html = f"""
<div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
  <div style="background: #59473c; color: white; padding: 24px; border-radius: 4px 4px 0 0;">
    <h1 style="margin: 0; font-size: 22px;">Payment confirmed</h1>
    <p style="margin: 6px 0 0; opacity: 0.9; font-size: 15px;">{weeks_mention}training plan{race_mention}</p>
  </div>

  <div style="background: #f9f9f7; padding: 24px; border: 1px solid #e0e0e0; border-top: none;">
    <p style="font-size: 15px; line-height: 1.6;">Hey {first_name},</p>

    <p style="font-size: 15px; line-height: 1.6;">Payment received — thank you.</p>

    <div style="margin: 20px 0; padding: 20px; background: #fff; border: 2px solid #1A8A82; border-radius: 6px;">
      <h3 style="margin: 0 0 8px; font-size: 16px; color: #59473c;">Your one action item</h3>
      <p style="margin: 0 0 16px; font-size: 14px; color: #555;">Connect to my coaching account on TrainingPeaks so I can push your workouts there:</p>
      <div style="text-align: center;">
        <a href="{tp_connect_url}" style="display: inline-block; background: #1A8A82; color: white; padding: 14px 32px; text-decoration: none; border-radius: 4px; font-size: 15px; font-weight: bold;">Connect on TrainingPeaks</a>
      </div>
      <p style="margin: 12px 0 0; font-size: 12px; color: #999; text-align: center;">Don't have a TrainingPeaks account? <a href="https://www.trainingpeaks.com/athlete-edition/" style="color: #1A8A82;">Create a free one first</a>, then click above.</p>
    </div>

    <h3 style="margin: 24px 0 12px; font-size: 15px; color: #59473c;">What happens next</h3>
    <ol style="font-size: 14px; padding-left: 20px; line-height: 2.2;">
      <li>Your custom {weeks_mention}training plan{race_mention} is <strong>being built right now</strong>.</li>
      <li>I'll <strong>review it personally</strong> and make sure everything is dialed.</li>
      <li>Within <strong>24 hours</strong>, your workouts will be live on your TrainingPeaks calendar.</li>
      <li>You'll get an email when it's ready with your <strong>training guide</strong> (PDF).</li>
    </ol>

    <div style="margin: 24px 0; padding: 12px 16px; background: #f5f5f0; border-left: 3px solid #B7950B;">
      <p style="margin: 0; font-size: 13px; color: #666;"><strong>Delivery timeline:</strong> Most plans are ready same-day. Maximum 24 hours. I'll email you the moment it's live.</p>
    </div>

    <p style="font-size: 14px; line-height: 1.6;">Questions? Reply to this email.</p>

    <p style="font-size: 14px; margin-top: 24px; color: #666;">— Matti, {brand_name}<br>
    <a href="{brand_cfg['site']}" style="color: #1A8A82;">{brand_site}</a></p>
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
        'error': _pipeline_error_excerpt(result) if not result.get('success') else '',
        # The plan delivered, but the automatic coach checks flagged it — review
        # coaching_brief.md before sending. Distinct from a clean delivery.
        'needs_review': 'GG_NEEDS_REVIEW=1' in stdout,
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

    # Brand is the strongest discipline signal: a Roadie Labs customer is a
    # ROAD athlete. derive_discipline checks profile['discipline'] first, so
    # without this a road order with an unknown race name fell through to the
    # gravel default and got gravel archetypes + a Gravel God guide.
    _brand = (metadata.get('brand') or '').lower()
    if _brand == 'roadielabs':
        profile['discipline'] = 'road'
    elif _brand == 'gravelgod':
        profile.setdefault('discipline', 'gravel')

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

    # The race the customer SELECTED on the site carries its slug — the pipeline
    # resolves the target race by this ID (exact), skipping fuzzy name-matching.
    target_slug = intake_data.get('race_slug') or a_race.get('slug', '') or ''

    # Brand is the strongest discipline signal: a Roadie Labs order is a ROAD
    # athlete. Carry it so an UNKNOWN race name doesn't fall through to the
    # gravel default (and a road customer gets a gravel plan + Gravel God guide).
    _brand = (intake_data.get('brand') or '').lower()
    _discipline_hint = {'roadielabs': 'road', 'gravelgod': 'gravel'}.get(_brand, '')

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
- Race Slug: {target_slug}
- Discipline: {_discipline_hint}
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
- Travel Dates: {intake_data.get('travel_dates', '') or 'None'}

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
            logger.error(
                f"Pipeline failed for {athlete_id}: "
                f"{_pipeline_error_excerpt({'stderr': result.stderr, 'stdout': result.stdout})}"
            )

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
    'personal_email.md',
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
        'error': _pipeline_error_excerpt(result) if not result['success'] else None,
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
# ASYNC PIPELINE JOBS — durable JSON job records + background threads
#
# The pipeline takes minutes; Stripe times out webhook responses at ~20s.
# The webhook handler now writes a job record to the persistent volume
# (DATA_DIR/jobs/{athlete_id}.json), spawns the pipeline in a background
# thread, and returns 200 to Stripe immediately. Job records survive
# Railway restarts; sweep_stuck_jobs() retries jobs orphaned mid-generation
# (on startup, hourly, and via POST /api/jobs/sweep for external cron).
#
# SYNC_PIPELINE=1 preserves the old inline path (tests / local debugging).
# =============================================================================

JOBS_DIR = os.path.join(DATA_DIR, 'jobs')

# A queued/running job untouched for this long is considered orphaned by a
# restart or crash and gets retried by the sweep (max JOB_MAX_ATTEMPTS).
JOB_STUCK_AFTER_MINUTES = int(os.environ.get('JOB_STUCK_AFTER_MINUTES', '30'))
JOB_MAX_ATTEMPTS = int(os.environ.get('JOB_MAX_ATTEMPTS', '2'))

# Serializes job-file writes within this process (cross-process safety comes
# from atomic tempfile + os.replace; gunicorn runs 2 workers).
_jobs_write_lock = threading.Lock()


def _sync_pipeline_mode() -> bool:
    """True when SYNC_PIPELINE=1 — run the pipeline inline in the request."""
    return os.environ.get('SYNC_PIPELINE', '') == '1'


def _job_path(athlete_id: str) -> Path:
    return Path(JOBS_DIR) / f'{athlete_id}.json'


def _write_job(job: dict):
    """Atomically persist a job record (temp file + os.replace)."""
    job['updated_at'] = datetime.now().isoformat()
    path = _job_path(job['athlete_id'])
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f'.{path.name}.tmp')
    with _jobs_write_lock:
        with open(tmp, 'w') as f:
            json.dump(job, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)


def _read_job(athlete_id: str) -> dict:
    """Load a job record. Returns None if absent or unreadable."""
    path = _job_path(athlete_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Unreadable job record {path.name}: {e}")
        return None


def _update_job(athlete_id: str, **fields) -> dict:
    """Read-modify-write a job record."""
    job = _read_job(athlete_id) or {'athlete_id': athlete_id}
    job.update(fields)
    _write_job(job)
    return job


def _execute_plan_job(job: dict, intake_data: dict = None):
    """Run the full generation flow for one job and keep its record updated.

    Runs in a background thread by default (inline when SYNC_PIPELINE=1).
    Preserves the exact behaviors of the old synchronous path: run pipeline
    → log order → persist zips → coach notification (success or FAILED).
    Never raises — a crashed job is marked failed and the operator notified
    loudly; the customer never sees an error (order-killer-prevention rule).

    Returns the pipeline result dict.
    """
    athlete_id = job['athlete_id']
    order_data = job.get('order_data', {})
    if intake_data is None and job.get('intake_id'):
        intake_data = load_intake(job['intake_id'])

    try:
        _update_job(athlete_id, status='running',
                    started_at=datetime.now().isoformat())

        result = run_pipeline(athlete_id, deliver=True,
                              intake_data=intake_data or None)
        log_order(order_data, result)

        if result['success']:
            try:
                persist_deliverables(athlete_id)
            except Exception as e:
                logger.error(f"Failed to persist deliverables for {athlete_id}: {e}")

        details = _build_plan_notification_details(order_data, result,
                                                   intake_data or None)
        if result['success']:
            details['download_token'] = _generate_download_token(athlete_id)
            _notify_new_order('training_plan', details)
            _update_job(athlete_id, status='succeeded',
                        finished_at=datetime.now().isoformat(), error=None)
        else:
            _notify_new_order('training_plan_FAILED', details)
            _update_job(athlete_id, status='failed',
                        finished_at=datetime.now().isoformat(),
                        error=_pipeline_error_excerpt(result))
        return result

    except Exception as e:
        # Loud to the operator, never customer-visible.
        logger.critical(
            f"PLAN JOB CRASHED for {athlete_id} "
            f"(order {job.get('order_id', '?')}): {e}", exc_info=True)
        try:
            _update_job(athlete_id, status='failed',
                        finished_at=datetime.now().isoformat(),
                        error=str(e)[:500])
            details = _build_plan_notification_details(
                order_data,
                {'success': False, 'stdout': '', 'stderr': str(e)[:500]},
                intake_data or None)
            _notify_new_order('training_plan_FAILED', details)
        except Exception:
            logger.exception(f"Failed to record job crash for {athlete_id}")
        return {'success': False, 'stdout': '', 'stderr': str(e)}


def _start_job_thread(job: dict, intake_data: dict = None) -> threading.Thread:
    """Spawn the job in a background (non-daemon) thread.

    Separate function so tests can patch it to run inline/deterministically.
    daemon=False: on graceful shutdown the worker waits for the thread
    (gunicorn --graceful-timeout 30); a hard kill is what the sweep handles.
    """
    t = threading.Thread(
        target=_execute_plan_job,
        args=(job,),
        kwargs={'intake_data': intake_data},
        name=f'plan-job-{job["athlete_id"]}',
        daemon=False,
    )
    t.start()
    return t


def _spawn_plan_job(order_data: dict, intake_id: str = '',
                    intake_data: dict = None) -> tuple:
    """Write a queued job record and launch generation.

    Returns (job, sync_result). sync_result is the pipeline result when
    SYNC_PIPELINE=1 (inline execution), else None (background thread).

    Guards against the same athlete's job running twice: if a queued or
    running job already exists for this athlete_id, no new one is spawned
    (webhook retries are already absorbed upstream by order idempotency).
    """
    athlete_id = order_data['athlete_id']

    existing = _read_job(athlete_id)
    if existing and existing.get('status') in ('queued', 'running'):
        logger.warning(
            f"Job for {athlete_id} already {existing['status']} "
            f"(order {existing.get('order_id', '?')}) — not spawning duplicate")
        return existing, None

    job = {
        'athlete_id': athlete_id,
        'order_id': order_data.get('order_id', ''),
        'intake_id': intake_id or '',
        'status': 'queued',
        'attempts': 1,
        'max_attempts': JOB_MAX_ATTEMPTS,
        'created_at': datetime.now().isoformat(),
        'started_at': None,
        'finished_at': None,
        'error': None,
        # Full order_data so sweep retries are self-contained after restart.
        'order_data': order_data,
    }
    _write_job(job)

    if _sync_pipeline_mode():
        result = _execute_plan_job(job, intake_data=intake_data)
        return job, result

    _start_job_thread(job, intake_data=intake_data)
    return job, None


def sweep_stuck_jobs() -> dict:
    """Retry jobs orphaned in queued/running (e.g. by a Railway restart).

    A job untouched for JOB_STUCK_AFTER_MINUTES is respawned with
    attempts+1; past JOB_MAX_ATTEMPTS it's marked failed and the operator
    is notified loudly. Runs on startup, hourly (before_request), and via
    POST /api/jobs/sweep (X-Cron-Secret) for external cron wiring.
    """
    stats = {'scanned': 0, 'retried': 0, 'failed': 0}
    jobs_dir = Path(JOBS_DIR)
    if not jobs_dir.exists():
        return stats

    stuck_before = datetime.now() - timedelta(minutes=JOB_STUCK_AFTER_MINUTES)

    for path in sorted(jobs_dir.glob('*.json')):
        job = _read_job(path.stem)
        if not job or job.get('status') not in ('queued', 'running'):
            continue
        stats['scanned'] += 1

        try:
            updated_at = datetime.fromisoformat(job.get('updated_at', ''))
        except (ValueError, TypeError):
            updated_at = datetime.min
        if updated_at > stuck_before:
            continue  # Recently touched — probably still running

        athlete_id = job['athlete_id']
        attempts = int(job.get('attempts', 1))
        max_attempts = int(job.get('max_attempts', JOB_MAX_ATTEMPTS))

        if attempts >= max_attempts:
            logger.critical(
                f"PLAN JOB ORPHANED after {attempts} attempts: {athlete_id} "
                f"(order {job.get('order_id', '?')}) — marking failed, "
                f"manual re-run required")
            _update_job(athlete_id, status='failed',
                        finished_at=datetime.now().isoformat(),
                        error=f'Job stuck after {attempts} attempts '
                              f'(likely restart mid-generation)')
            try:
                details = _build_plan_notification_details(
                    job.get('order_data', {}),
                    {'success': False, 'stdout': '',
                     'stderr': f'Job orphaned after {attempts} attempts — '
                               f'likely a restart mid-generation. '
                               f'Re-run the pipeline manually.'},
                    None)
                _notify_new_order('training_plan_FAILED', details)
            except Exception:
                logger.exception(f"Failed to notify for orphaned job {athlete_id}")
            stats['failed'] += 1
        else:
            job['attempts'] = attempts + 1
            job['status'] = 'queued'
            job['error'] = None
            _write_job(job)
            logger.warning(
                f"Retrying stuck job for {athlete_id} "
                f"(attempt {job['attempts']}/{max_attempts})")
            if _sync_pipeline_mode():
                _execute_plan_job(job)
            else:
                _start_job_thread(job)
            stats['retried'] += 1

    return stats


# =============================================================================
# ROUTES
# =============================================================================




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


# Order/session references: Stripe session ids (cs_...), test ids, or
# athlete ids. Never used as a filesystem path without validation.
_ORDER_REF_RE = re.compile(r'^[A-Za-z0-9_-]{1,128}$')

# Customer-facing status copy — honest, never an error or a "we broke".
_MSG_IN_PROGRESS = ("Your custom plan is being generated right now — "
                    "you'll get an email as soon as it's ready.")
_MSG_FINISHING = ("We're putting the finishing touches on your plan "
                  "and will email it to you shortly.")
_MSG_READY = "Your plan is ready — check your email for the details."


@app.route('/api/order-status/<ref>', methods=['GET'])
@limiter.limit("30/minute")
def order_status(ref):
    """Customer-facing order status for the success page.

    <ref> is either the Stripe checkout session id (the success page gets
    ?session_id={CHECKOUT_SESSION_ID}) or an athlete id. Returns
    {status, download_ready, message} where status is ready|processing|
    unknown. A failed job reads as "processing" with a gentle finishing
    message — failures are loud to the operator (email/logs), invisible
    to the customer.
    """
    if not ref or not _ORDER_REF_RE.match(ref):
        return jsonify({'status': 'unknown', 'download_ready': False}), 404

    athlete_id = None
    is_session_ref = ref.startswith('cs_') or ref.startswith('test_')
    if is_session_ref:
        # Map session/order id → athlete via the idempotency ledger
        processed_file = Path(DATA_DIR) / '.processed_orders.json'
        try:
            if processed_file.exists():
                entry = json.loads(processed_file.read_text()).get(ref)
                if entry:
                    athlete_id = entry.get('athlete_id', '')
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"order-status: could not read processed orders: {e}")
        if not athlete_id:
            # Stripe's webhook may simply not have arrived yet — honest
            # in-progress, never an error the customer has to interpret.
            return jsonify({'status': 'processing', 'download_ready': False,
                            'message': _MSG_IN_PROGRESS})
    else:
        athlete_id = _normalize_athlete_id(ref.lower())
        if not validate_athlete_id(athlete_id):
            return jsonify({'status': 'unknown', 'download_ready': False}), 404

    norm_id = _normalize_athlete_id(athlete_id)
    customer_zip = Path(DELIVERIES_DIR) / norm_id / f'{norm_id}-training-plan.zip'
    download_ready = customer_zip.exists()

    job = _read_job(norm_id) or {}
    job_status = job.get('status', '')

    if download_ready or job_status == 'succeeded':
        return jsonify({'status': 'ready', 'download_ready': download_ready,
                        'message': _MSG_READY})
    if job_status in ('queued', 'running'):
        return jsonify({'status': 'processing', 'download_ready': False,
                        'message': _MSG_IN_PROGRESS})
    if job_status == 'failed':
        # Operator already notified loudly; the customer sees a calm
        # "finishing up" — the coach recovers the order manually.
        return jsonify({'status': 'processing', 'download_ready': False,
                        'message': _MSG_FINISHING})
    if is_session_ref:
        # Order known (idempotency mark) but no job record — legacy or
        # sync-mode order. Report in-progress; email delivery still applies.
        return jsonify({'status': 'processing', 'download_ready': False,
                        'message': _MSG_IN_PROGRESS})
    return jsonify({'status': 'unknown', 'download_ready': False}), 404


@app.route('/api/jobs/sweep', methods=['POST'])
@limiter.limit("5/minute")
def jobs_sweep():
    """Retry jobs orphaned by a restart. Secured by X-Cron-Secret.

    Also runs automatically on startup and hourly; this endpoint exists so
    an external cron can add a third safety net (wire later — do NOT add a
    GitHub workflow here).
    """
    secret = request.headers.get('X-Cron-Secret', '')
    if not CRON_SECRET:
        return jsonify({'error': 'CRON_SECRET not configured'}), 503
    if not hmac.compare_digest(secret, CRON_SECRET):
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        stats = sweep_stuck_jobs()
        logger.info(f"Job sweep complete: {stats}")
        return jsonify({'status': 'ok', **stats})
    except Exception as e:
        logger.exception(f"Job sweep error: {e}")
        return jsonify({'error': 'Internal error'}), 500


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

    # The intake email promises the training guide — attach it. PDF when
    # the pipeline produced one, HTML otherwise (Railway has no Chrome,
    # so the PDF is often absent server-side; Jesse Couch never got his).
    guide_attachments = []
    for guide_name in ('training_guide.pdf', 'training_guide.html'):
        guide_path = delivery_dir / guide_name
        if guide_path.exists():
            guide_attachments.append((guide_name, str(guide_path)))
            break

    # Check for personalized email generated by the pipeline
    personal_email_path = delivery_dir / 'personal_email.md'
    if personal_email_path.exists():
        try:
            personal_md = personal_email_path.read_text().strip()
            # Extract subject line (first line starting with **Subject:**)
            subject = f'Your training plan{race_mention} is live on TrainingPeaks'
            for line in personal_md.split('\n'):
                if line.startswith('**Subject:**'):
                    subject = line.replace('**Subject:**', '').strip()
                    break

            # Strip the subject line from body
            body_lines = [l for l in personal_md.split('\n')
                          if not l.startswith('**Subject:**')]
            text_body = '\n'.join(body_lines).strip()

            # Convert markdown bold to HTML
            import re
            html_body = text_body
            html_body = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_body)
            html_body = html_body.replace('\n\n', '</p><p style="font-size: 15px; line-height: 1.6;">')
            html_body = html_body.replace('\n', '<br>')
            html_body = f"""
<div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
  <div style="background: #59473c; color: white; padding: 24px; border-radius: 4px 4px 0 0;">
    <h1 style="margin: 0; font-size: 22px;">Your plan is live</h1>
    {f'<p style="margin: 6px 0 0; opacity: 0.9; font-size: 15px;">{race_name}</p>' if race_name else ''}
  </div>
  <div style="background: #f9f9f7; padding: 24px; border: 1px solid #e0e0e0; border-top: none;">
    <p style="font-size: 15px; line-height: 1.6;">{html_body}</p>
  </div>
</div>"""

            ok = _send_email(customer_email, subject, text_body, html=html_body,
                             reply_to=NOTIFICATION_EMAIL,
                             attachments=guide_attachments)
            if ok:
                logger.info(f"Sent personal email to {_mask_email(customer_email)} for {norm_id}")
                return jsonify({
                    'status': 'confirmed',
                    'athlete_id': norm_id,
                    'email': _mask_email(customer_email),
                    'source': 'personal_email.md',
                })
            else:
                return jsonify({'error': 'Failed to send personal email'}), 502
        except Exception as e:
            logger.warning(f"Failed to load personal_email.md, falling back to generic: {e}")

    # --- Fallback: generic confirmation email ---
    subject = f'Your training plan{race_mention} is live on TrainingPeaks'

    text_body = f"""Hey {first_name},

Your custom training plan{race_mention} is built, reviewed, and live on TrainingPeaks.

Here's what to do:
1. Connect with me on TrainingPeaks: https://home.trainingpeaks.com/attachtocoach?sharedKey=2OTEPC6BXNVQU
2. Your calendar now has every workout loaded, day by day, through race week.
3. Each workout has target power zones, duration, and structure — just follow the plan.
4. Do today's workout. Don't overthink it.

A few things to know:
- Week 1 is calibration. It may feel easy. That's intentional.
- If life gets in the way and you miss a day, skip it and move on. Don't double up.
- I can see your completed workouts in TP. I'm watching — in a good way.

If you have questions at any point, just reply to this email.

— Matti, Gravel God Cycling
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
      <li><strong><a href="https://home.trainingpeaks.com/attachtocoach?sharedKey=2OTEPC6BXNVQU" style="color: #1A8A82;">Connect with me on TrainingPeaks</a></strong> — click this link to attach to my coach account.</li>
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


    <p style="font-size: 14px; margin-top: 24px; color: #666;">— Matti, Gravel God Cycling<br>
    <a href="https://gravelgodcycling.com" style="color: #1A8A82;">gravelgodcycling.com</a></p>
  </div>
</div>"""

    ok = _send_email(customer_email, subject, text_body, html=html_body,
                     reply_to=NOTIFICATION_EMAIL,
                     attachments=guide_attachments)
    if ok:
        logger.info(f"Sent plan confirmation to {_mask_email(customer_email)} for {norm_id}")
        return jsonify({
            'status': 'confirmed',
            'athlete_id': norm_id,
            'email': _mask_email(customer_email),
        })
    else:
        return jsonify({'error': 'Failed to send confirmation email'}), 502


@app.route('/api/questionnaire-started', methods=['POST', 'OPTIONS'])
@limiter.limit("10/minute")
def questionnaire_started():
    """Log when a user fills in name + email on the questionnaire.

    Stores contact info so we can follow up if they abandon the form
    before reaching Stripe checkout. Deduplicates by email within 24hrs.
    """
    if request.method == 'OPTIONS':
        return '', 204

    data = request.get_json(silent=True)
    if not data:
        return '', 204  # Fail silently — this is a beacon

    email = (data.get('email') or '').strip().lower()
    name = (data.get('name') or '').strip()
    if not email or '@' not in email:
        return '', 204

    # Store in monthly questionnaire-starts log (dedup by email within 24hrs)
    log_dir = Path(DATA_DIR) / '.logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    starts_file = log_dir / f"questionnaire-starts-{now.strftime('%Y-%m')}.jsonl"

    # Check current + previous month for recent duplicate (24hr window can span months)
    prev_month = (now.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')
    files_to_check = [starts_file, log_dir / f"questionnaire-starts-{prev_month}.jsonl"]
    try:
        for check_file in files_to_check:
            if not check_file.exists():
                continue
            with open(check_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if (entry.get('email') == email and
                                (now - datetime.fromisoformat(entry['timestamp'])).total_seconds() < 86400):
                            return jsonify({'status': 'already_tracked'}), 200
                    except (json.JSONDecodeError, KeyError):
                        continue
    except IOError:
        pass

    entry = {
        'timestamp': now.isoformat(),
        'email': email,
        'name': name,
        'sections_reached': data.get('sections_reached', 0),
        'source': data.get('source', ''),
        'user_agent': request.headers.get('User-Agent', '')[:200],
    }

    try:
        with open(starts_file, 'a') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(json.dumps(entry) + '\n')
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except IOError as e:
        logger.error(f"Failed to log questionnaire start: {e}")

    logger.info(f"Questionnaire started: {_mask_email(email)} ({name.split()[0] if name else '?'})")

    # Notify coach of new questionnaire start
    if NOTIFICATION_EMAIL and RESEND_API_KEY:
        subject = f"Questionnaire started: {name or 'Unknown'}"
        body = (
            f"Someone started the training plan questionnaire.\n\n"
            f"Name: {name}\n"
            f"Email: {email}\n"
            f"Time: {now.strftime('%Y-%m-%d %H:%M')} UTC\n\n"
            f"If they don't complete checkout within a few hours, "
            f"consider a personal follow-up.\n"
        )
        _send_email(NOTIFICATION_EMAIL, subject, body)

    return jsonify({'status': 'tracked'}), 200


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

    # Brand follows the requesting site (gravelgodcycling.com / roadielabs.com)
    brand = _brand_from_origin(request.headers.get('Origin', ''))
    brand_cfg = _brand_config(brand)

    # Generate intake ID and store questionnaire data
    intake_id = str(uuid.uuid4())
    data['computed_price_cents'] = pricing['price_cents']
    data['computed_weeks'] = pricing['weeks']
    data['brand'] = brand
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
                'brand': brand,
            },
            success_url=f"{brand_cfg['site']}/training-plans/success/?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{brand_cfg['site']}{brand_cfg['questionnaire_path']}",
            expires_at=expires_at,
            after_expiration={
                'recovery': {
                    'enabled': True,
                    'allow_promotion_codes': True,
                }
            },
            consent_collection={
                'promotions': 'auto',
            },
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
            consent_collection={
                'promotions': 'auto',
            },
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
            consent_collection={
                'promotions': 'auto',
            },
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

        # Queue generation, return immediately (same async path as Stripe).
        job, sync_result = _spawn_plan_job(order_data)

        if sync_result is not None:
            # SYNC_PIPELINE=1 — legacy inline path (tests / local debugging)
            if sync_result['success']:
                return jsonify({
                    'status': 'success',
                    'athlete_id': athlete_id,
                    'message': 'Training plan generated and delivered'
                })
            return jsonify({
                'status': 'pipeline_failed',
                'athlete_id': athlete_id,
                'message': 'Order received but pipeline failed. Manual intervention required.'
            })

        return jsonify({
            'status': 'accepted',
            'athlete_id': athlete_id,
            'job_status': job.get('status', 'queued'),
            'message': 'Training plan generation queued'
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

        # Health monitors create never-paid sessions that expire hourly —
        # without this guard, enabling checkout.session.expired turns them
        # into a recovery-email firehose (guard added when the event
        # subscription was finally enabled, Jul 2026).
        MONITOR_EMAILS = ('checkout-monitor@', 'healthcheck@', 'monitor@',
                          'gravelgodcoaching@gmail.com')
        if email and any(email.lower().startswith(m) or m in email.lower()
                         for m in MONITOR_EMAILS):
            logger.info(f"Expired checkout {session_id} — monitor session, skipping recovery")
            return jsonify({'status': 'ignored', 'reason': 'Monitor session'})

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
            f"— Matti, Gravel God Cycling\n"
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
            f"— Matti, Gravel God Cycling\n"
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
            f"— Matti, Gravel God Cycling\n"
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

    # Record purchase in GA4 (server-side, consent-independent)
    session_obj = data.get('data', {}).get('object', {})
    brand = session_obj.get('metadata', {}).get('brand', DEFAULT_BRAND)
    _send_ga4_purchase(order_data['order_id'], session_obj.get('amount_total'),
                       'training_plan', 'Custom Training Plan', brand=brand)

    # Send instant payment confirmation to customer (before pipeline runs)
    customer_email = order_data['profile'].get('email', '')
    customer_name = order_data['profile'].get('name', '')
    race_name = intake_data.get('race_name', '') if intake_data else ''
    _send_payment_confirmation(customer_email, customer_name, race_name=race_name,
                               brand=brand)

    # Queue generation and return 200 to Stripe immediately — the pipeline
    # takes minutes, Stripe times out at ~20s. The background job handles
    # log_order, ZIP persistence, and the coach notification email.
    job, sync_result = _spawn_plan_job(order_data, intake_id=intake_id,
                                       intake_data=intake_data or None)

    if sync_result is not None:
        # SYNC_PIPELINE=1 — legacy inline path (tests / local debugging)
        if sync_result['success']:
            return jsonify({
                'status': 'success',
                'athlete_id': athlete_id,
                'message': 'Training plan generated and delivered'
            })
        return jsonify({
            'status': 'pipeline_failed',
            'athlete_id': athlete_id,
            'message': 'Order received but pipeline failed. Manual intervention required.'
        })

    return jsonify({
        'status': 'accepted',
        'athlete_id': athlete_id,
        'job_status': job.get('status', 'queued'),
        'message': 'Training plan generation queued'
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
    _send_ga4_purchase(order_id, session.get('amount_total'),
                       'coaching', f'Coaching ({tier})',
                       brand=metadata.get('brand', DEFAULT_BRAND))
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
    _send_ga4_purchase(order_id, session.get('amount_total'),
                       'consulting', 'Consulting Session',
                       brand=metadata.get('brand', DEFAULT_BRAND))
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
# Canonical copy lives in webhook/email_templates.py (zero-dep module,
# voice rules + tests in webhook/tests/test_email_templates.py).
from email_templates import FOLLOWUP_SEQUENCE  # noqa: E402


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


# =============================================================================
# LIFECYCLE TOUCHPOINTS — plan-aware anti-churn emails
#
# Unlike the fixed day-1/3/7 FOLLOWUP_SEQUENCE, these are computed from the
# athlete's actual plan calendar (plan_dates.yaml): FTP-rescale offer after
# the testing week, reassurance at the first recovery week, a mid-plan
# survey, B-race debriefs, race-week checklist, and the post-race
# survey + coaching offer. All reply-driven: responses land in the coach
# inbox and become coaching-funnel conversations.
# =============================================================================

def compute_touchpoints(plan_dates: dict, first_name: str, race_name: str) -> list:
    """Compute the lifecycle touchpoint schedule for one athlete's plan.

    Returns a list of {'date': 'YYYY-MM-DD', 'key': str, 'subject': str,
    'body': str}, sorted by date. Dates come from plan_dates.yaml — the
    same calendar that drives workout generation, so touches always match
    the plan the athlete is actually riding.
    """
    from datetime import timedelta as _td

    weeks = plan_dates.get('weeks', [])
    if not weeks:
        return []

    def _d(s):
        return datetime.strptime(s, '%Y-%m-%d')

    def _iso(dt):
        return dt.strftime('%Y-%m-%d')

    touches = []
    plan_start = plan_dates.get('plan_start', '')
    race_date = plan_dates.get('race_date', '')

    # 1. Setup check — day 2 of the plan
    if plan_start:
        touches.append({
            'date': _iso(_d(plan_start) + _td(days=1)),
            'key': 'setup_check',
            'subject': 'Quick check — did everything load OK?',
            'body': (
                f"Hey {first_name},\n\n"
                "You're one day into the plan. Quick check: did the workouts "
                "load into TrainingPeaks OK, and did the first session sync "
                "to your head unit?\n\n"
                "If anything looks off, just hit reply and I'll sort it out "
                "today.\n\nMatti\nGravel God Cycling"
            ),
        })

    # 2. FTP rescale offer — end of week 1 (testing week)
    if weeks:
        w1_sunday = weeks[0].get('sunday', '')
        if w1_sunday:
            touches.append({
                'date': w1_sunday,
                'key': 'ftp_rescale',
                'subject': 'Got your test results? Reply and I\'ll rescale your plan',
                'body': (
                    f"Hey {first_name},\n\n"
                    "Week 1 testing is done. If your FTP came out different "
                    "from what you put in the questionnaire, reply with the "
                    "new number and I'll rescale every remaining workout in "
                    "your plan to match. Takes me minutes, keeps every "
                    "interval honest.\n\n"
                    "This is the difference between a static plan and one "
                    "that adapts with you — use it.\n\nMatti"
                ),
            })

    # 3. First recovery week — reassurance
    for w in weeks:
        if w.get('is_recovery_week'):
            touches.append({
                'date': w.get('monday', ''),
                'key': 'recovery_note',
                'subject': 'This week is supposed to feel easy',
                'body': (
                    f"Hey {first_name},\n\n"
                    "You just hit your first recovery week. The volume drop "
                    "is intentional — this is where your body banks the "
                    "fitness from the last block. Don't add workouts, don't "
                    "extend rides. Feeling fresh by Sunday IS the workout.\n\n"
                    "If you're NOT feeling recovered by end of week, reply "
                    "and tell me — that's signal worth acting on.\n\nMatti"
                ),
            })
            break

    # 4. Mid-plan survey — ~45% through
    if len(weeks) >= 6:
        mid_week = weeks[max(1, round(len(weeks) * 0.45)) - 1]
        touches.append({
            'date': mid_week.get('monday', ''),
            'key': 'midplan_survey',
            'subject': f'Halfway check-in — 3 quick questions',
            'body': (
                f"Hey {first_name},\n\n"
                "You're around the halfway mark. Three questions — just hit "
                "reply with one-line answers:\n\n"
                "1. Are you finishing the hard days, or surviving them?\n"
                "2. Is the plan too hard, too easy, or about right?\n"
                "3. What's getting in the way, if anything?\n\n"
                "I read every reply and adjust plans when the answers call "
                "for it.\n\nMatti"
            ),
        })

    # 5. B-race debriefs — day after each B-race
    seen_b = set()
    for w in weeks:
        b = w.get('b_race')
        if b and b.get('date') and b['date'] not in seen_b:
            seen_b.add(b['date'])
            touches.append({
                'date': _iso(_d(b['date']) + _td(days=1)),
                'key': f"b_debrief_{b['date']}",
                'subject': f"How did {b.get('name', 'the race')} go?",
                'body': (
                    f"Hey {first_name},\n\n"
                    f"How was {b.get('name', 'the race')}? Reply with the "
                    "short version — result, how the legs felt, anything "
                    "that surprised you. If something's off, there's still "
                    "time to tune the final block before "
                    f"{race_name}.\n\nMatti"
                ),
            })

    # 6. Race-week checklist — Monday of race week
    race_week_monday = plan_dates.get('race_week_monday', '')
    if race_week_monday:
        touches.append({
            'date': race_week_monday,
            'key': 'race_week',
            'subject': f'Race week. Here\'s your checklist.',
            'body': (
                f"Hey {first_name},\n\n"
                f"It's race week for {race_name}. The work is done — "
                "nothing you do this week makes you fitter, plenty makes "
                "you slower. Checklist:\n\n"
                "- Follow the taper exactly. Openers sharpen, they don't train\n"
                "- Fueling: practice nothing new on race day; your race-day "
                "carb targets are in your fueling plan\n"
                "- Equipment check Saturday ride: tires, sealant, bolts, bags\n"
                "- Sleep is the priority. Wednesday night matters more than "
                "the night before\n\n"
                "Go get it. Reply if anything feels off.\n\nMatti"
            ),
        })

    # 7. Post-race — survey + coaching bridge
    if race_date:
        touches.append({
            'date': _iso(_d(race_date) + _td(days=1)),
            'key': 'postrace',
            'subject': f'How did {race_name} go?',
            'body': (
                f"Hey {first_name},\n\n"
                f"You did it. However {race_name} went, I want to hear it — "
                "reply with:\n\n"
                "1. Your result (and how it compared to your goal)\n"
                "2. The single best and worst moment of the day\n"
                "3. Would you recommend this plan to a riding buddy? "
                "(honest answer)\n\n"
                "And if this race lit the fire for the next one: my coaching "
                "roster has a spot open, and plan customers who join within "
                "two weeks get their first month's plan adjustments built "
                "off everything we just learned about you. Reply 'coaching' "
                "and I'll send details.\n\nMatti"
            ),
        })

    touches = [t for t in touches if t.get('date')]
    touches.sort(key=lambda t: t['date'])
    return touches


def process_touchpoint_emails():
    """Send lifecycle touchpoints due today. Returns stats dict.

    Stateless: recomputes each athlete's schedule from plan_dates.yaml on
    every run and dedupes via the followup sent-log (key = 'tp:<key>').
    """
    log_dir = Path(DATA_DIR) / '.logs'
    if not log_dir.exists():
        return {'checked': 0, 'sent': 0, 'errors': 0}

    sent = _get_sent_followups()
    today = datetime.utcnow().strftime('%Y-%m-%d')
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
    stats = {'checked': 0, 'sent': 0, 'errors': 0}

    for log_file in sorted(log_dir.glob('20*.jsonl')):
        for line in log_file.read_text().strip().split('\n'):
            if not line:
                continue
            try:
                order = json.loads(line)
            except json.JSONDecodeError:
                continue
            if order.get('product_type') != 'training_plan':
                continue
            if not order.get('success', True):
                continue

            athlete_id = order.get('athlete_id', '')
            email = order.get('email', '')
            name = order.get('name', '')
            order_id = order.get('order_id', '')
            if not athlete_id or not email or not order_id:
                continue

            plan_dates_path = (Path(ATHLETES_DIR)
                               / athlete_id.replace('_', '-')
                               / 'plan_dates.yaml')
            if not plan_dates_path.exists():
                plan_dates_path = Path(ATHLETES_DIR) / athlete_id / 'plan_dates.yaml'
            if not plan_dates_path.exists():
                continue

            try:
                with open(plan_dates_path) as f:
                    plan_dates = yaml.safe_load(f) or {}
            except (OSError, yaml.YAMLError):
                continue

            stats['checked'] += 1
            first_name = name.split()[0] if name else 'there'
            race_name = order.get('race_name', 'your race')

            for touch in compute_touchpoints(plan_dates, first_name, race_name):
                # Due today (or yesterday — 1-day catch-up window)
                if touch['date'] not in (today, yesterday):
                    continue
                dedupe_key = (order_id, f"tp:{touch['key']}")
                if dedupe_key in sent:
                    continue
                try:
                    _send_email(
                        to=email,
                        subject=touch['subject'],
                        body=touch['body'],
                        reply_to=NOTIFICATION_EMAIL or None,
                    )
                    _mark_followup_sent(order_id, f"tp:{touch['key']}", email)
                    sent.add(dedupe_key)
                    stats['sent'] += 1
                    logger.info(
                        f"Touchpoint {touch['key']} sent to "
                        f"{_mask_email(email)} (order {order_id})"
                    )
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Touchpoint send failed: {e}")

    return stats


@app.route('/api/intel-stats', methods=['GET'])
@limiter.limit("10/minute")
def intel_stats():
    """Last-24h commerce ground truth for the Morning Intel report.

    The report previously inferred orders from GA4 events; this endpoint
    exposes the actual ledger (/data/.logs) — orders WITH fulfillment
    outcomes, cart-recovery sends, and questionnaire starts — so a paying
    customer whose pipeline failed is never invisible.

    Secured by the same X-Cron-Secret as the cron endpoints.
    """
    secret = request.headers.get('X-Cron-Secret', '')
    if not CRON_SECRET:
        return jsonify({'error': 'CRON_SECRET not configured'}), 503
    if not hmac.compare_digest(secret, CRON_SECRET):
        return jsonify({'error': 'Unauthorized'}), 401

    from datetime import timedelta as _td
    now = datetime.now()
    cutoff = (now - _td(hours=24)).isoformat()
    log_dir = Path(DATA_DIR) / '.logs'
    months = {now.strftime('%Y-%m'),
              (now.replace(day=1) - _td(days=1)).strftime('%Y-%m')}

    def _monitor(email):
        e = (email or '').lower()
        return (not e or 'monitor' in e or 'healthcheck' in e
                or 'gravelgodcoaching@' in e or 'example.com' in e)

    orders, recoveries = [], []
    for m in sorted(months):
        f = log_dir / f'{m}.jsonl'
        if not f.exists():
            continue
        for line in f.read_text().splitlines():
            try:
                e = json.loads(line)
            except (ValueError, TypeError):
                continue
            if (e.get('timestamp') or '') < cutoff or _monitor(e.get('email')):
                continue
            if e.get('product_type') == 'cart_recovery' or 'recovery_url_sent' in e:
                recoveries.append({'timestamp': e.get('timestamp'),
                                   'email': e.get('email'),
                                   'product': e.get('original_product')})
            else:
                orders.append({'timestamp': e.get('timestamp'),
                               'product_type': e.get('product_type'),
                               'email': e.get('email'),
                               'name': e.get('name'),
                               'success': e.get('success'),
                               'error': (e.get('error') or '')[:200] or None})

    q_starts = 0
    for m in sorted(months):
        f = log_dir / f'questionnaire-starts-{m}.jsonl'
        if not f.exists():
            continue
        for line in f.read_text().splitlines():
            try:
                e = json.loads(line)
            except (ValueError, TypeError):
                continue
            if (e.get('timestamp') or e.get('ts') or '') >= cutoff and \
                    not _monitor(e.get('email')) and e.get('src') != 'health-check':
                q_starts += 1

    return jsonify({
        'window_hours': 24,
        'orders': orders,
        'failed_orders': [o for o in orders if o.get('success') is False],
        'recoveries': recoveries,
        'questionnaire_starts': q_starts,
    })


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
        tp_stats = process_touchpoint_emails()
        logger.info(f"Touchpoint cron complete: {tp_stats}")
        return jsonify({'status': 'ok', **stats,
                        'touchpoints': tp_stats})
    except Exception as e:
        logger.exception(f"Follow-up cron error: {e}")
        return jsonify({'error': 'Internal error'}), 500


# =============================================================================
# ENGINE — deterministic block generation for Endure Labs (Convergence Phase 1)
# =============================================================================

@app.route('/engine/block', methods=['POST'])
@limiter.limit("60/minute")
def engine_block():
    """POST /engine/block — deterministic training-block generation.

    Exposes the block-builder core so Endure Labs generates blocks in <1s
    instead of a 30s LLM call. Contract is FROZEN (see engine_adapter.py):
    - Auth: X-Engine-Secret vs ENGINE_SHARED_SECRET (503 unset, 401 mismatch)
    - 400 invalid request (with field errors)
    - 422 compliance gate CRITICAL failure
    - 500 unexpected

    ADDITIVE July 2026: each response week carries a structured `strength`
    object (sessions + avoidSameDayAs) alongside the unchanged
    `strengthProtocol` prose string — see engine_adapter._structured_strength
    for the shape. No existing fields or request validation changed.
    """
    secret = request.headers.get('X-Engine-Secret', '')
    expected = os.environ.get('ENGINE_SHARED_SECRET', '')
    if not expected:
        return jsonify({'error': 'ENGINE_SHARED_SECRET not configured'}), 503
    if not hmac.compare_digest(secret, expected):
        return jsonify({'error': 'Unauthorized'}), 401

    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({'error': 'invalid_request',
                        'fields': {'body': 'Request body must be JSON'}}), 400

    try:
        from engine_adapter import (
            validate_request as engine_validate,
            generate_block as engine_generate,
            ComplianceFailure,
        )
    except Exception as e:
        logger.exception(f"Engine adapter import failed: {e}")
        return jsonify({'error': 'Internal error'}), 500

    params, field_errors = engine_validate(payload)
    if field_errors:
        return jsonify({'error': 'invalid_request', 'fields': field_errors}), 400

    try:
        result = engine_generate(params)
    except ComplianceFailure as cf:
        logger.warning(
            f"Engine block compliance gate failed: {cf.compliance['violations']}")
        return jsonify({'error': 'compliance_failed',
                        'compliance': cf.compliance}), 422
    except Exception as e:
        logger.exception(f"Engine block generation failed: {e}")
        return jsonify({'error': 'Internal error'}), 500

    logger.info(
        f"Engine block generated: phase={params['phase']} weeks={params['weeks']} "
        f"archetype={params['archetype']} methodology={params['methodology']} "
        f"in {result['engine']['generated_ms']}ms")
    return jsonify(result)


# =============================================================================
# STARTUP
# =============================================================================

# Clean up stale intake files on startup
try:
    cleanup_stale_intakes()
except Exception as e:
    logger.warning(f"Intake cleanup on startup failed: {e}")

# Crash durability: retry jobs orphaned by a restart mid-generation.
# Only touches queued/running records older than JOB_STUCK_AFTER_MINUTES,
# so a fresh deploy doesn't double-run anything actively in flight.
try:
    _startup_sweep = sweep_stuck_jobs()
    if _startup_sweep.get('retried') or _startup_sweep.get('failed'):
        logger.warning(f"Startup job sweep: {_startup_sweep}")
except Exception as e:
    logger.error(f"Startup job sweep failed: {e}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
