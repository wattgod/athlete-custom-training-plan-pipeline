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
from pathlib import Path
from datetime import datetime, timedelta, date
from flask import Flask, request, jsonify
import stripe
import yaml

app = Flask(__name__)

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

# CORS — only allow requests from our site
ALLOWED_ORIGINS = ['https://gravelgodcycling.com', 'https://www.gravelgodcycling.com']

# Configure Stripe
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# Validate required config in production
if IS_PRODUCTION:
    if not STRIPE_WEBHOOK_SECRET:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET required in production")
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
    'min': 'price_1T2ekSLoaHDbEqSqY10rhBJE',   # $199/mo
    'mid': 'price_1T2ekTLoaHDbEqSqCZ8dLEYk',   # $299/mo
    'max': 'price_1T2ekULoaHDbEqSqLoY8g0BD',   # $1,200/mo
}

CONSULTING_PRICE_ID = 'price_1T2ekVLoaHDbEqSq0GGfoBEX'  # $150/hr

# Intake data expiry (24 hours)
INTAKE_EXPIRY_HOURS = 24

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

    processed_file = Path(ATHLETES_DIR) / '.processed_orders.json'

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

    processed_file = Path(ATHLETES_DIR) / '.processed_orders.json'
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
    """Get or create the intake storage directory."""
    intake_dir = Path(ATHLETES_DIR) / '.intake'
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
    """Delete intake files older than INTAKE_EXPIRY_HOURS."""
    intake_dir = get_intake_dir()
    cutoff = datetime.now() - timedelta(hours=INTAKE_EXPIRY_HOURS)
    cleaned = 0

    for intake_file in intake_dir.glob('*.json'):
        try:
            mtime = datetime.fromtimestamp(intake_file.stat().st_mtime)
            if mtime < cutoff:
                intake_file.unlink()
                cleaned += 1
        except OSError as e:
            logger.warning(f"Error cleaning intake file {intake_file}: {e}")

    if cleaned:
        logger.info(f"Cleaned {cleaned} stale intake files")


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

def run_pipeline(athlete_id: str, deliver: bool = True) -> dict:
    """Run the full training plan pipeline with timeout."""
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

    logger.info(f"Running pipeline for {athlete_id}")

    try:
        result = subprocess.run(
            cmd,
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
# LOGGING
# =============================================================================

def log_order(order_data: dict, result: dict):
    """Log order processing for tracking with file locking."""
    log_dir = Path(ATHLETES_DIR) / '.logs'
    log_dir.mkdir(exist_ok=True)

    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'athlete_id': order_data['athlete_id'],
        'order_id': order_data['order_id'],
        'tier': order_data['tier'],
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

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint with dependency checks."""
    checks = {
        'service': 'gravel-god-webhook',
        'status': 'ok',
        'athletes_dir': Path(ATHLETES_DIR).exists(),
        'scripts_dir': Path(SCRIPTS_DIR).exists(),
    }

    if not checks['athletes_dir'] or not checks['scripts_dir']:
        checks['status'] = 'degraded'

    status_code = 200 if checks['status'] == 'ok' else 503
    return jsonify(checks), status_code


@app.route('/api/create-checkout', methods=['POST', 'OPTIONS'])
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

        checkout_session = stripe.checkout.Session.create(
            line_items=line_items,
            mode='payment',
            customer_email=email,
            client_reference_id=intake_id,
            metadata={
                'intake_id': intake_id,
                'product_type': 'training_plan',
                'tier': 'custom',
                'athlete_name': name,
                'weeks': str(pricing['weeks']),
                'price_cents': str(pricing['price_cents']),
            },
            success_url='https://gravelgodcycling.com/training-plans/success/',
            cancel_url='https://gravelgodcycling.com/training-plans/questionnaire/',
        )

        logger.info(f"Created checkout session {checkout_session.id} for intake {intake_id} "
                     f"({pricing['weeks']}wk, {pricing['price_display']})")

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
        checkout_session = stripe.checkout.Session.create(
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='subscription',
            customer_email=email,
            metadata={
                'product_type': 'coaching',
                'tier': tier,
                'athlete_name': name,
            },
            success_url='https://gravelgodcycling.com/coaching/welcome/',
            cancel_url='https://gravelgodcycling.com/coaching/',
        )

        logger.info(f"Created coaching checkout {checkout_session.id} "
                     f"(tier={tier}, email={email})")

        return jsonify({'checkout_url': checkout_session.url})

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error creating coaching checkout: {e}")
        return jsonify({'error': 'Payment service error. Please try again.'}), 502
    except Exception as e:
        logger.exception(f"Coaching checkout error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/create-consulting-checkout', methods=['POST', 'OPTIONS'])
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
        checkout_session = stripe.checkout.Session.create(
            line_items=[{'price': CONSULTING_PRICE_ID, 'quantity': hours}],
            mode='payment',
            customer_email=email,
            metadata={
                'product_type': 'consulting',
                'athlete_name': name,
                'hours': str(hours),
            },
            success_url='https://gravelgodcycling.com/consulting/confirmed/',
            cancel_url='https://gravelgodcycling.com/consulting/',
        )

        logger.info(f"Created consulting checkout {checkout_session.id} "
                     f"({hours}hr, email={email})")

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
        result = run_pipeline(athlete_id, deliver=True)

        # Mark as processed even if pipeline failed (to prevent retries)
        mark_order_processed(order_data['order_id'], athlete_id)
        log_order(order_data, result)

        if result['success']:
            return jsonify({
                'status': 'success',
                'athlete_id': athlete_id,
                'message': 'Training plan generated and delivered'
            })
        else:
            # Log error but return 200 (webhook processed, pipeline failed)
            return jsonify({
                'status': 'pipeline_failed',
                'athlete_id': athlete_id,
                'message': 'Order received but pipeline failed. Manual intervention required.'
            })

    except Exception as e:
        logger.exception(f"WooCommerce webhook error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe checkout.session.completed webhook."""
    signature = request.headers.get('Stripe-Signature', '')

    if not verify_stripe_signature(request.data, signature):
        logger.warning("Invalid Stripe signature")
        return jsonify({'error': 'Invalid signature'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400

    event_type = data.get('type', '')

    # Only process completed checkouts
    if event_type != 'checkout.session.completed':
        return jsonify({'status': 'ignored', 'reason': f'Event type: {event_type}'})

    try:
        session = data.get('data', {}).get('object', {})
        metadata = session.get('metadata', {})
        product_type = metadata.get('product_type', 'training_plan')
        order_id = session.get('id', '')

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


def _handle_training_plan_webhook(data: dict, order_id: str) -> tuple:
    """Handle training plan checkout completion — create profile + run pipeline."""
    order_data = extract_stripe_data(data)

    is_valid, error_msg = validate_order_data(order_data)
    if not is_valid:
        logger.error(f"Invalid order data: {error_msg}")
        return jsonify({'error': error_msg}), 400

    athlete_id, profile_path = create_athlete_profile(order_data)
    result = run_pipeline(athlete_id, deliver=True)

    mark_order_processed(order_data['order_id'], athlete_id)
    log_order(order_data, result)

    if result['success']:
        return jsonify({
            'status': 'success',
            'athlete_id': athlete_id,
            'message': 'Training plan generated and delivered'
        })
    else:
        return jsonify({
            'status': 'pipeline_failed',
            'athlete_id': athlete_id,
            'message': 'Order received but pipeline failed. Manual intervention required.'
        })


def _handle_coaching_webhook(session: dict, metadata: dict, order_id: str) -> tuple:
    """Handle coaching subscription checkout completion — log + notify."""
    tier = metadata.get('tier', 'unknown')
    name = metadata.get('athlete_name', 'Unknown')
    email = session.get('customer_details', {}).get('email', '')
    subscription_id = session.get('subscription', '')

    logger.info(f"Coaching subscription started: {name} ({email}), "
                f"tier={tier}, subscription={subscription_id}")

    mark_order_processed(order_id, sanitize_athlete_id(name))

    log_dir = Path(ATHLETES_DIR) / '.logs'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"{datetime.now().strftime('%Y-%m')}.jsonl"
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'product_type': 'coaching',
        'tier': tier,
        'name': name,
        'email': email,
        'order_id': order_id,
        'subscription_id': subscription_id,
        'success': True,
    }
    try:
        with open(log_file, 'a') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(json.dumps(log_entry) + '\n')
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except IOError as e:
        logger.error(f"Failed to write coaching log: {e}")

    return jsonify({
        'status': 'success',
        'product_type': 'coaching',
        'tier': tier,
        'message': f'Coaching subscription ({tier}) started for {name}'
    })


def _handle_consulting_webhook(session: dict, metadata: dict, order_id: str) -> tuple:
    """Handle consulting checkout completion — log + notify."""
    name = metadata.get('athlete_name', 'Unknown')
    hours = metadata.get('hours', '1')
    email = session.get('customer_details', {}).get('email', '')

    logger.info(f"Consulting booked: {name} ({email}), {hours}hr")

    mark_order_processed(order_id, sanitize_athlete_id(name))

    log_dir = Path(ATHLETES_DIR) / '.logs'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"{datetime.now().strftime('%Y-%m')}.jsonl"
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'product_type': 'consulting',
        'name': name,
        'email': email,
        'hours': hours,
        'order_id': order_id,
        'success': True,
    }
    try:
        with open(log_file, 'a') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.write(json.dumps(log_entry) + '\n')
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except IOError as e:
        logger.error(f"Failed to write consulting log: {e}")

    return jsonify({
        'status': 'success',
        'product_type': 'consulting',
        'hours': hours,
        'message': f'Consulting ({hours}hr) booked for {name}'
    })


# Test endpoint only available in non-production
if not IS_PRODUCTION:
    @app.route('/webhook/test', methods=['POST'])
    def test_webhook():
        """Test endpoint for development only."""
        data = request.get_json() or {}

        order_data = {
            'athlete_id': sanitize_athlete_id(data.get('athlete_id', 'test_athlete')),
            'order_id': 'test_' + datetime.now().strftime('%Y%m%d%H%M%S'),
            'tier': data.get('tier', 'custom'),
            'profile': data.get('profile', {
                'name': 'Test Athlete',
                'email': 'test@example.com',
                'target_race': {
                    'name': 'Test Race',
                    'date': '2025-06-01',
                    'distance_miles': 100,
                }
            })
        }

        if not validate_athlete_id(order_data['athlete_id']):
            return jsonify({'error': 'Invalid athlete ID'}), 400

        try:
            athlete_id, profile_path = create_athlete_profile(order_data)

            if data.get('run_pipeline', False):
                result = run_pipeline(athlete_id, deliver=False)
                return jsonify({
                    'status': 'success' if result['success'] else 'error',
                    'athlete_id': athlete_id,
                    'profile_path': str(profile_path),
                    'pipeline': result
                })

            return jsonify({
                'status': 'success',
                'athlete_id': athlete_id,
                'profile_path': str(profile_path),
                'message': 'Profile created (pipeline not run)'
            })

        except Exception as e:
            logger.exception(f"Test webhook error: {e}")
            return jsonify({'error': 'Internal server error'}), 500


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
