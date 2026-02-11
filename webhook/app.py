"""
Gravel God Webhook Receiver

Receives WooCommerce/Stripe webhooks after successful payment,
triggers the training plan pipeline, and delivers to athlete.

Deploy to: Railway, Render, or Vercel (free tier works)
"""

import os
import re
import json
import hmac
import fcntl
import hashlib
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify
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
ATHLETES_DIR = os.environ.get('ATHLETES_DIR', '/app/athletes')
SCRIPTS_DIR = os.environ.get('SCRIPTS_DIR', '/app/athletes/scripts')

# Validate required config in production
if IS_PRODUCTION:
    if not WOOCOMMERCE_SECRET and not STRIPE_WEBHOOK_SECRET:
        raise RuntimeError("At least one of WOOCOMMERCE_SECRET or STRIPE_WEBHOOK_SECRET required in production")

# Tier configuration
TIERS = {
    'starter': {'max_weeks': 8, 'price': 99},
    'race_ready': {'max_weeks': 16, 'price': 149},
    'full_build': {'max_weeks': 52, 'price': 199},
}

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
        import stripe
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
    """Extract athlete info from Stripe checkout session."""
    session = data.get('data', {}).get('object', {})
    metadata = session.get('metadata', {})
    customer_details = session.get('customer_details', {})

    name = customer_details.get('name', metadata.get('name', 'Unknown')).strip()
    athlete_id = sanitize_athlete_id(name)

    # Determine tier from amount or metadata
    amount = session.get('amount_total', 0) / 100  # cents to dollars
    tier = metadata.get('tier')
    if not tier:
        if amount <= 99:
            tier = 'starter'
        elif amount <= 149:
            tier = 'race_ready'
        else:
            tier = 'full_build'

    return {
        'athlete_id': athlete_id,
        'order_id': session.get('id', ''),
        'tier': tier,
        'profile': {
            'name': name,
            'email': customer_details.get('email', '').strip().lower(),
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
        order_data = extract_stripe_data(data)

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

    except Exception as e:
        logger.exception(f"Stripe webhook error: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# Test endpoint only available in non-production
if not IS_PRODUCTION:
    @app.route('/webhook/test', methods=['POST'])
    def test_webhook():
        """Test endpoint for development only."""
        data = request.get_json() or {}

        order_data = {
            'athlete_id': sanitize_athlete_id(data.get('athlete_id', 'test_athlete')),
            'order_id': 'test_' + datetime.now().strftime('%Y%m%d%H%M%S'),
            'tier': data.get('tier', 'race_ready'),
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
# MAIN
# =============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
