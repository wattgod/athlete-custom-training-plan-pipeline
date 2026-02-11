#!/usr/bin/env python3
"""
Gravel God Training Plan Web App

Flask-based web interface for the training plan generation pipeline.
"""

import os
import re
import sys
import json
import secrets
import subprocess
from pathlib import Path
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, abort
from flask_wtf.csrf import CSRFProtect

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).parent.parent / "athletes" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from constants import (
    get_athlete_dir,
    get_athlete_file,
    get_athlete_current_plan_dir,
    load_athlete_yaml,
    DAY_ORDER_FULL,
)

app = Flask(__name__)

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

# Secret key - MUST be set in production
_secret_key = os.environ.get('SECRET_KEY')
if not _secret_key:
    if os.environ.get('FLASK_ENV') == 'production':
        raise RuntimeError("SECRET_KEY environment variable is required in production")
    _secret_key = secrets.token_hex(32)  # Generate random key for dev
    print("WARNING: Using randomly generated SECRET_KEY. Set SECRET_KEY env var for production.")
app.secret_key = _secret_key

# CSRF Protection
csrf = CSRFProtect(app)

# Security headers
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    if os.environ.get('FLASK_ENV') == 'production':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


# =============================================================================
# AUTHENTICATION
# =============================================================================

# Simple API key auth for now - can be upgraded to OAuth later
API_KEY = os.environ.get('GG_API_KEY')
ADMIN_PASSWORD = os.environ.get('GG_ADMIN_PASSWORD')


def require_auth(f):
    """Decorator to require authentication on routes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Check session-based auth
        if session.get('authenticated'):
            return f(*args, **kwargs)

        # Check API key in header
        api_key = request.headers.get('X-API-Key')
        if api_key and API_KEY and secrets.compare_digest(api_key, API_KEY):
            return f(*args, **kwargs)

        # If no auth configured, allow access (dev mode)
        if not API_KEY and not ADMIN_PASSWORD:
            return f(*args, **kwargs)

        # Redirect to login for browser requests
        if request.accept_mimetypes.accept_html:
            return redirect(url_for('login', next=request.url))

        # Return 401 for API requests
        return jsonify({"error": "Authentication required"}), 401

    return decorated


def require_api_auth(f):
    """Decorator for API-only endpoints that require auth."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key and API_KEY and secrets.compare_digest(api_key, API_KEY):
            return f(*args, **kwargs)

        # If no API key configured, allow access (dev mode)
        if not API_KEY:
            return f(*args, **kwargs)

        return jsonify({"error": "Invalid or missing API key"}), 401

    return decorated


# =============================================================================
# INPUT VALIDATION
# =============================================================================

# Strict athlete ID validation - alphanumeric, hyphens, underscores only
ATHLETE_ID_PATTERN = re.compile(r'^[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]$|^[a-z0-9]$')
MAX_ATHLETE_ID_LENGTH = 64


def validate_athlete_id(athlete_id: str) -> bool:
    """Validate athlete ID is safe for filesystem use."""
    if not athlete_id:
        return False
    if len(athlete_id) > MAX_ATHLETE_ID_LENGTH:
        return False
    if not ATHLETE_ID_PATTERN.match(athlete_id):
        return False
    # Extra safety: no path traversal
    if '..' in athlete_id or '/' in athlete_id or '\\' in athlete_id:
        return False
    return True


def sanitize_athlete_id(name: str) -> str:
    """Convert a name to a safe athlete ID."""
    # Lowercase, replace spaces with hyphens
    safe_id = name.lower().strip()
    safe_id = re.sub(r'\s+', '-', safe_id)
    # Remove any character that's not alphanumeric, hyphen, or underscore
    safe_id = re.sub(r'[^a-z0-9_-]', '', safe_id)
    # Collapse multiple hyphens
    safe_id = re.sub(r'-+', '-', safe_id)
    # Remove leading/trailing hyphens
    safe_id = safe_id.strip('-')
    # Truncate to max length
    safe_id = safe_id[:MAX_ATHLETE_ID_LENGTH]
    return safe_id


def require_valid_athlete(f):
    """Decorator to validate athlete_id parameter."""
    @wraps(f)
    def decorated(athlete_id, *args, **kwargs):
        if not validate_athlete_id(athlete_id):
            if request.accept_mimetypes.accept_html:
                abort(404)
            return jsonify({"error": "Invalid athlete ID"}), 400
        return f(athlete_id, *args, **kwargs)
    return decorated


# =============================================================================
# CONFIGURATION
# =============================================================================

ATHLETES_DIR = Path(__file__).parent.parent / "athletes"


def get_all_athletes():
    """Get list of all athlete directories."""
    athletes = []
    for path in ATHLETES_DIR.iterdir():
        if path.is_dir() and not path.name.startswith('.') and path.name != 'scripts':
            if not validate_athlete_id(path.name):
                continue  # Skip invalid directories
            profile = load_athlete_yaml(path.name, "profile.yaml")
            if profile:
                athletes.append({
                    'id': path.name,
                    'name': profile.get('name', path.name),
                    'email': profile.get('email', ''),
                    'race': profile.get('target_race', {}).get('name', 'No race'),
                    'race_date': profile.get('target_race', {}).get('date', ''),
                })
    return sorted(athletes, key=lambda x: x['name'])


def run_pipeline_step(script_name: str, athlete_id: str) -> tuple:
    """Run a single pipeline script and return (success, output)."""
    # Validate script name against whitelist
    allowed_scripts = {
        'validate_profile.py',
        'derive_classifications.py',
        'select_methodology.py',
        'calculate_fueling.py',
        'build_weekly_structure.py',
        'generate_athlete_package.py',
        'generate_html_guide.py',
        'generate_dashboard.py',
        'create_profile_from_form.py',
    }

    if script_name not in allowed_scripts:
        return False, f"Script not allowed: {script_name}"

    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        return False, f"Script not found: {script_name}"

    try:
        result = subprocess.run(
            [sys.executable, str(script_path), athlete_id],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(ATHLETES_DIR.parent)
        )
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr or result.stdout
    except subprocess.TimeoutExpired:
        return False, "Timeout after 2 minutes"
    except subprocess.SubprocessError as e:
        return False, f"Subprocess error: {type(e).__name__}"


# =============================================================================
# AUTH ROUTES
# =============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if request.method == 'POST':
        password = request.form.get('password', '')
        if ADMIN_PASSWORD and secrets.compare_digest(password, ADMIN_PASSWORD):
            session['authenticated'] = True
            session.permanent = True
            next_url = request.args.get('next', url_for('index'))
            return redirect(next_url)
        flash("Invalid password", "error")
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout and clear session."""
    session.clear()
    flash("Logged out successfully", "success")
    return redirect(url_for('login'))


# =============================================================================
# ROUTES
# =============================================================================

@app.route('/')
@require_auth
def index():
    """Home page - list all athletes."""
    athletes = get_all_athletes()
    return render_template('index.html', athletes=athletes)


@app.route('/athlete/<athlete_id>')
@require_auth
@require_valid_athlete
def athlete_detail(athlete_id: str):
    """Athlete detail page with all their data."""
    profile = load_athlete_yaml(athlete_id, "profile.yaml")
    if not profile:
        flash(f"Athlete not found: {athlete_id}", "error")
        return redirect(url_for('index'))

    derived = load_athlete_yaml(athlete_id, "derived.yaml") or {}
    methodology = load_athlete_yaml(athlete_id, "methodology.yaml") or {}
    fueling = load_athlete_yaml(athlete_id, "fueling.yaml") or {}
    weekly_structure = load_athlete_yaml(athlete_id, "weekly_structure.yaml") or {}

    # Check what outputs exist
    athlete_dir = get_athlete_dir(athlete_id)
    current_plan_dir = get_athlete_current_plan_dir(athlete_id)

    outputs = {
        'has_derived': (athlete_dir / "derived.yaml").exists(),
        'has_methodology': (athlete_dir / "methodology.yaml").exists(),
        'has_fueling': (athlete_dir / "fueling.yaml").exists(),
        'has_weekly_structure': (athlete_dir / "weekly_structure.yaml").exists(),
        'has_dashboard': (athlete_dir / "dashboard.html").exists(),
        'has_guide': (current_plan_dir / "training_guide.html").exists(),
        'has_workouts': (current_plan_dir / "workouts").exists(),
    }

    return render_template('athlete_detail.html',
        athlete_id=athlete_id,
        profile=profile,
        derived=derived,
        methodology=methodology,
        fueling=fueling,
        weekly_structure=weekly_structure,
        outputs=outputs,
    )


@app.route('/athlete/<athlete_id>/dashboard')
@require_auth
@require_valid_athlete
def athlete_dashboard(athlete_id: str):
    """Serve the generated dashboard HTML."""
    dashboard_path = get_athlete_dir(athlete_id) / "dashboard.html"
    if dashboard_path.exists():
        # Sanitize output - it's our own generated HTML but be safe
        return dashboard_path.read_text()
    else:
        flash("Dashboard not generated yet. Run the pipeline first.", "warning")
        return redirect(url_for('athlete_detail', athlete_id=athlete_id))


@app.route('/athlete/<athlete_id>/guide')
@require_auth
@require_valid_athlete
def athlete_guide(athlete_id: str):
    """Serve the generated training guide HTML."""
    guide_path = get_athlete_current_plan_dir(athlete_id) / "training_guide.html"
    if guide_path.exists():
        return guide_path.read_text()
    else:
        flash("Training guide not generated yet. Run the pipeline first.", "warning")
        return redirect(url_for('athlete_detail', athlete_id=athlete_id))


@app.route('/new', methods=['GET', 'POST'])
@require_auth
def new_athlete():
    """Create new athlete from intake form."""
    if request.method == 'POST':
        form_data = request.form.to_dict()

        # Validate required fields
        name = form_data.get('name', '').strip()
        if not name:
            flash("Name is required", "error")
            return render_template('intake_form.html', form_data=form_data)

        if len(name) > 100:
            flash("Name is too long (max 100 characters)", "error")
            return render_template('intake_form.html', form_data=form_data)

        # Generate safe athlete ID
        athlete_id = sanitize_athlete_id(name)
        if not athlete_id:
            flash("Could not generate valid athlete ID from name", "error")
            return render_template('intake_form.html', form_data=form_data)

        # Check if already exists
        if get_athlete_dir(athlete_id).exists():
            flash(f"Athlete '{athlete_id}' already exists", "error")
            return render_template('intake_form.html', form_data=form_data)

        # Validate numeric fields
        try:
            if form_data.get('age'):
                age = int(form_data['age'])
                if not (10 <= age <= 100):
                    raise ValueError("Age must be between 10 and 100")
            if form_data.get('weight_kg'):
                weight = float(form_data['weight_kg'])
                if not (30 <= weight <= 200):
                    raise ValueError("Weight must be between 30 and 200 kg")
            if form_data.get('ftp_watts'):
                ftp = int(form_data['ftp_watts'])
                if not (50 <= ftp <= 600):
                    raise ValueError("FTP must be between 50 and 600 watts")
        except ValueError as e:
            flash(str(e), "error")
            return render_template('intake_form.html', form_data=form_data)

        # Save form data as JSON for processing
        form_json_path = ATHLETES_DIR.parent / "temp" / f"{athlete_id}_form.json"
        form_json_path.parent.mkdir(exist_ok=True)
        with open(form_json_path, 'w') as f:
            json.dump(form_data, f, indent=2)

        # Run profile creation
        success, output = run_pipeline_step("create_profile_from_form.py", athlete_id)

        if success:
            flash(f"Created athlete: {name}", "success")
            return redirect(url_for('athlete_detail', athlete_id=athlete_id))
        else:
            flash(f"Error creating profile: {output}", "error")
            return render_template('intake_form.html', form_data=form_data)

    return render_template('intake_form.html', form_data={})


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.route('/api/athletes')
@require_api_auth
def api_athletes():
    """API: Get all athletes."""
    return jsonify(get_all_athletes())


@app.route('/api/athlete/<athlete_id>')
@require_api_auth
@require_valid_athlete
def api_athlete(athlete_id: str):
    """API: Get athlete data."""
    profile = load_athlete_yaml(athlete_id, "profile.yaml")
    if not profile:
        return jsonify({"error": "Athlete not found"}), 404

    return jsonify({
        "profile": profile,
        "derived": load_athlete_yaml(athlete_id, "derived.yaml"),
        "methodology": load_athlete_yaml(athlete_id, "methodology.yaml"),
        "fueling": load_athlete_yaml(athlete_id, "fueling.yaml"),
    })


@app.route('/api/athlete/<athlete_id>/generate', methods=['POST'])
@require_api_auth
@require_valid_athlete
@csrf.exempt  # API endpoints use API key auth instead
def api_generate(athlete_id: str):
    """API: Run full pipeline for athlete."""
    profile = load_athlete_yaml(athlete_id, "profile.yaml")
    if not profile:
        return jsonify({"error": "Athlete not found"}), 404

    steps = [
        ("validate_profile.py", "Validate Profile"),
        ("derive_classifications.py", "Derive Classifications"),
        ("select_methodology.py", "Select Methodology"),
        ("calculate_fueling.py", "Calculate Fueling"),
        ("build_weekly_structure.py", "Build Weekly Structure"),
        ("generate_athlete_package.py", "Generate Workouts"),
        ("generate_html_guide.py", "Generate Guide"),
        ("generate_dashboard.py", "Generate Dashboard"),
    ]

    results = []
    all_success = True

    for script, name in steps:
        success, output = run_pipeline_step(script, athlete_id)
        results.append({
            "step": name,
            "success": success,
            "output": output[:500] if output else ""
        })
        if not success:
            all_success = False
            break

    return jsonify({
        "success": all_success,
        "results": results
    })


@app.route('/api/athlete/<athlete_id>/step/<step_name>', methods=['POST'])
@require_api_auth
@require_valid_athlete
@csrf.exempt  # API endpoints use API key auth instead
def api_run_step(athlete_id: str, step_name: str):
    """API: Run a single pipeline step."""
    valid_steps = {
        'validate': 'validate_profile.py',
        'derive': 'derive_classifications.py',
        'methodology': 'select_methodology.py',
        'fueling': 'calculate_fueling.py',
        'structure': 'build_weekly_structure.py',
        'workouts': 'generate_athlete_package.py',
        'guide': 'generate_html_guide.py',
        'dashboard': 'generate_dashboard.py',
    }

    if step_name not in valid_steps:
        return jsonify({"error": f"Invalid step: {step_name}"}), 400

    success, output = run_pipeline_step(valid_steps[step_name], athlete_id)
    return jsonify({
        "success": success,
        "output": output
    })


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found(e):
    if request.accept_mimetypes.accept_html:
        return render_template('error.html', error="Page not found", code=404), 404
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def server_error(e):
    if request.accept_mimetypes.accept_html:
        return render_template('error.html', error="Internal server error", code=500), 500
    return jsonify({"error": "Internal server error"}), 500


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Default to false in production, true only if explicitly set
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
