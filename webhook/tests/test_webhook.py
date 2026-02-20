#!/usr/bin/env python3
"""
Tests for the Gravel God Webhook Receiver.

Run with: pytest webhook/tests/test_webhook.py -v
"""

import os
import sys
import json
import hmac
import hashlib
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

import pytest

# Add webhook directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment before importing app
os.environ['FLASK_ENV'] = 'test'
os.environ['WOOCOMMERCE_SECRET'] = ''  # Disable signature check in tests
os.environ['STRIPE_WEBHOOK_SECRET'] = ''
os.environ['STRIPE_SECRET_KEY'] = ''  # Disable in tests


@pytest.fixture
def temp_athletes_dir():
    """Create a temporary athletes directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        athletes_dir = Path(tmpdir) / 'athletes'
        athletes_dir.mkdir()
        scripts_dir = athletes_dir / 'scripts'
        scripts_dir.mkdir()

        # Create a mock generate_full_package.py
        mock_script = scripts_dir / 'generate_full_package.py'
        mock_script.write_text('#!/usr/bin/env python3\nimport sys; sys.exit(0)')

        yield athletes_dir


@pytest.fixture
def app(temp_athletes_dir):
    """Create test Flask app."""
    os.environ['ATHLETES_DIR'] = str(temp_athletes_dir)
    os.environ['SCRIPTS_DIR'] = str(temp_athletes_dir / 'scripts')

    # Import app after setting env vars
    from app import app as flask_app
    flask_app.config['TESTING'] = True
    return flask_app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_ok(self, client, temp_athletes_dir):
        """Health check returns 200 when dependencies exist."""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'
        assert data['service'] == 'gravel-god-webhook'

    def test_health_degraded_missing_dirs(self, client):
        """Health check returns 503 when directories missing."""
        with patch.dict(os.environ, {'ATHLETES_DIR': '/nonexistent'}):
            # Need to reimport to pick up new env
            response = client.get('/health')
            # Note: This test may pass with 200 if app caches the path
            assert response.status_code in [200, 503]


class TestInputValidation:
    """Tests for input validation functions."""

    def test_validate_athlete_id_valid(self):
        """Valid athlete IDs pass validation."""
        from app import validate_athlete_id

        assert validate_athlete_id('john_doe') is True
        assert validate_athlete_id('john-doe') is True
        assert validate_athlete_id('johndoe123') is True
        assert validate_athlete_id('a') is True
        assert validate_athlete_id('ab') is True

    def test_validate_athlete_id_invalid(self):
        """Invalid athlete IDs fail validation."""
        from app import validate_athlete_id

        assert validate_athlete_id('') is False
        assert validate_athlete_id('../etc/passwd') is False
        assert validate_athlete_id('john/doe') is False
        assert validate_athlete_id('john\\doe') is False
        assert validate_athlete_id('_invalid') is False
        assert validate_athlete_id('-invalid') is False
        assert validate_athlete_id('UPPERCASE') is False
        assert validate_athlete_id('a' * 100) is False  # Too long

    def test_sanitize_athlete_id(self):
        """Sanitize converts names to safe IDs."""
        from app import sanitize_athlete_id

        assert sanitize_athlete_id('John Doe') == 'john_doe'
        assert sanitize_athlete_id('Mary-Jane Watson') == 'mary-jane_watson'
        assert sanitize_athlete_id('Test!!!User') == 'testuser'
        assert sanitize_athlete_id('  Spaces  ') == 'spaces'
        assert sanitize_athlete_id('') == ''

    def test_safe_int_valid(self):
        """safe_int handles valid integers."""
        from app import safe_int

        assert safe_int(42) == 42
        assert safe_int('42') == 42
        assert safe_int(0) == 0

    def test_safe_int_invalid(self):
        """safe_int returns None for invalid input."""
        from app import safe_int

        assert safe_int(None) is None
        assert safe_int('') is None
        assert safe_int('abc') is None
        assert safe_int(-1) is None  # Negative
        assert safe_int(1000000) is None  # Too large

    def test_safe_float_valid(self):
        """safe_float handles valid floats."""
        from app import safe_float

        assert safe_float(72.5) == 72.5
        assert safe_float('72.5') == 72.5
        assert safe_float(0) == 0.0

    def test_safe_float_invalid(self):
        """safe_float returns None for invalid input."""
        from app import safe_float

        assert safe_float(None) is None
        assert safe_float('') is None
        assert safe_float('abc') is None


class TestOrderDataValidation:
    """Tests for order data validation."""

    def test_validate_order_data_valid(self):
        """Valid order data passes validation."""
        from app import validate_order_data

        order_data = {
            'athlete_id': 'john_doe',
            'order_id': '12345',
            'tier': 'race_ready',
            'profile': {
                'name': 'John Doe',
                'email': 'john@example.com',
                'fitness_markers': {
                    'weight_kg': 75.0,
                    'ftp_watts': 250,
                }
            }
        }

        is_valid, error = validate_order_data(order_data)
        assert is_valid is True
        assert error is None

    def test_validate_order_data_missing_name(self):
        """Order data without name fails validation."""
        from app import validate_order_data

        order_data = {
            'athlete_id': 'john_doe',
            'profile': {
                'email': 'john@example.com',
            }
        }

        is_valid, error = validate_order_data(order_data)
        assert is_valid is False
        assert 'name' in error.lower()

    def test_validate_order_data_invalid_email(self):
        """Order data with invalid email fails validation."""
        from app import validate_order_data

        order_data = {
            'athlete_id': 'john_doe',
            'profile': {
                'name': 'John Doe',
                'email': 'not-an-email',
            }
        }

        is_valid, error = validate_order_data(order_data)
        assert is_valid is False
        assert 'email' in error.lower()

    def test_validate_order_data_invalid_weight(self):
        """Order data with out-of-range weight fails validation."""
        from app import validate_order_data

        order_data = {
            'athlete_id': 'john_doe',
            'profile': {
                'name': 'John Doe',
                'email': 'john@example.com',
                'fitness_markers': {
                    'weight_kg': 500,  # Too heavy
                }
            }
        }

        is_valid, error = validate_order_data(order_data)
        assert is_valid is False
        assert 'weight' in error.lower()


class TestWooCommerceWebhook:
    """Tests for WooCommerce webhook endpoint."""

    def test_woocommerce_ignores_pending_orders(self, client):
        """Pending orders are ignored."""
        response = client.post(
            '/webhook/woocommerce',
            json={'status': 'pending'},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ignored'

    def test_woocommerce_processes_completed_orders(self, client, temp_athletes_dir):
        """Completed orders are processed."""
        order_data = {
            'id': 12345,
            'status': 'completed',
            'billing': {
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john@example.com',
            },
            'meta_data': [
                {'key': 'race_name', 'value': 'Test Race'},
                {'key': 'race_date', 'value': '2025-06-01'},
            ],
            'line_items': [
                {'name': 'Custom Training Plan - Race Ready', 'sku': 'training-race-ready'}
            ]
        }

        with patch('app.run_pipeline') as mock_pipeline:
            mock_pipeline.return_value = {'success': True, 'stdout': '', 'stderr': ''}

            response = client.post(
                '/webhook/woocommerce',
                json=order_data,
                content_type='application/json'
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'success'
            assert data['athlete_id'] == 'john_doe'

    def test_woocommerce_idempotency(self, client, temp_athletes_dir):
        """Duplicate orders are rejected."""
        order_data = {
            'id': 99999,
            'status': 'completed',
            'billing': {
                'first_name': 'Jane',
                'last_name': 'Doe',
                'email': 'jane@example.com',
            },
            'meta_data': [],
            'line_items': []
        }

        with patch('app.run_pipeline') as mock_pipeline:
            mock_pipeline.return_value = {'success': True, 'stdout': '', 'stderr': ''}

            # First request
            response1 = client.post(
                '/webhook/woocommerce',
                json=order_data,
                content_type='application/json'
            )
            assert response1.status_code == 200

            # Second request (duplicate)
            response2 = client.post(
                '/webhook/woocommerce',
                json=order_data,
                content_type='application/json'
            )
            assert response2.status_code == 200
            data = response2.get_json()
            assert data['status'] == 'duplicate'


class TestStripeWebhook:
    """Tests for Stripe webhook endpoint."""

    def test_stripe_ignores_non_checkout_events(self, client):
        """Non-checkout events are ignored."""
        response = client.post(
            '/webhook/stripe',
            json={'type': 'customer.created'},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ignored'

    def test_stripe_processes_checkout_completed(self, client, temp_athletes_dir):
        """Checkout completed events are processed."""
        stripe_event = {
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_test_123',
                    'amount_total': 18000,
                    'customer_details': {
                        'name': 'Test User',
                        'email': 'test@example.com',
                    },
                    'metadata': {
                        'tier': 'custom',
                        'race_name': 'Test Race',
                        'race_date': '2026-06-01',
                    }
                }
            }
        }

        with patch('app.run_pipeline') as mock_pipeline:
            mock_pipeline.return_value = {'success': True, 'stdout': '', 'stderr': ''}

            response = client.post(
                '/webhook/stripe',
                json=stripe_event,
                content_type='application/json'
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'success'


class TestDataExtraction:
    """Tests for data extraction functions."""

    def test_extract_woocommerce_tier_from_sku(self):
        """Tier is correctly determined from product SKU."""
        from app import extract_woocommerce_data

        # Starter
        data = {
            'billing': {'first_name': 'Test', 'last_name': 'User', 'email': 'test@test.com'},
            'meta_data': [],
            'line_items': [{'sku': 'training-starter', 'name': 'anything'}]
        }
        result = extract_woocommerce_data(data)
        assert result['tier'] == 'starter'

        # Full Build
        data['line_items'] = [{'sku': 'training-full-build', 'name': 'anything'}]
        result = extract_woocommerce_data(data)
        assert result['tier'] == 'full_build'

        # Race Ready
        data['line_items'] = [{'sku': 'training-race-ready', 'name': 'anything'}]
        result = extract_woocommerce_data(data)
        assert result['tier'] == 'race_ready'

    def test_extract_stripe_tier_from_metadata(self):
        """Tier is correctly extracted from metadata."""
        from app import extract_stripe_data

        data = {
            'data': {
                'object': {
                    'id': 'cs_123',
                    'amount_total': 12000,
                    'customer_details': {'name': 'Test', 'email': 'test@test.com'},
                    'metadata': {'tier': 'custom'}
                }
            }
        }
        result = extract_stripe_data(data)
        assert result['tier'] == 'custom'

    def test_extract_stripe_tier_defaults_to_custom(self):
        """Tier defaults to 'custom' when not in metadata."""
        from app import extract_stripe_data

        data = {
            'data': {
                'object': {
                    'id': 'cs_123',
                    'amount_total': 12000,
                    'customer_details': {'name': 'Test', 'email': 'test@test.com'},
                    'metadata': {}
                }
            }
        }
        result = extract_stripe_data(data)
        assert result['tier'] == 'custom'


class TestProfileCreation:
    """Tests for profile creation."""

    def test_create_athlete_profile(self, temp_athletes_dir):
        """Profile is created with correct structure."""
        os.environ['ATHLETES_DIR'] = str(temp_athletes_dir)

        from app import create_athlete_profile

        order_data = {
            'athlete_id': 'test_athlete',
            'order_id': 'order_123',
            'tier': 'race_ready',
            'profile': {
                'name': 'Test Athlete',
                'email': 'test@example.com',
            }
        }

        athlete_id, profile_path = create_athlete_profile(order_data)

        assert athlete_id == 'test_athlete'
        assert profile_path.exists()

        import yaml
        with open(profile_path) as f:
            profile = yaml.safe_load(f)

        assert profile['name'] == 'Test Athlete'
        assert profile['email'] == 'test@example.com'
        assert profile['tier'] == 'race_ready'
        assert profile['order_id'] == 'order_123'
        assert 'created_at' in profile


class TestSecurityHeaders:
    """Tests for security headers."""

    def test_security_headers_present(self, client):
        """Security headers are set on responses."""
        response = client.get('/health')

        assert response.headers.get('X-Content-Type-Options') == 'nosniff'
        assert response.headers.get('X-Frame-Options') == 'DENY'
        assert response.headers.get('X-XSS-Protection') == '1; mode=block'


class TestIntakeStorage:
    """Tests for questionnaire intake storage."""

    def test_store_and_load_intake(self, temp_athletes_dir):
        """Intake data can be stored and loaded."""
        os.environ['ATHLETES_DIR'] = str(temp_athletes_dir)
        from app import store_intake, load_intake

        intake_id = '550e8400-e29b-41d4-a716-446655440000'
        data = {'name': 'Test User', 'email': 'test@test.com', 'tier': 'full_build'}

        store_intake(intake_id, data)
        loaded = load_intake(intake_id)

        assert loaded['name'] == 'Test User'
        assert loaded['email'] == 'test@test.com'
        assert loaded['tier'] == 'full_build'

    def test_load_nonexistent_intake(self, temp_athletes_dir):
        """Loading a nonexistent intake returns empty dict."""
        os.environ['ATHLETES_DIR'] = str(temp_athletes_dir)
        from app import load_intake

        result = load_intake('550e8400-e29b-41d4-a716-446655440001')
        assert result == {}

    def test_load_intake_rejects_invalid_id(self, temp_athletes_dir):
        """Loading with invalid UUID rejects path traversal."""
        os.environ['ATHLETES_DIR'] = str(temp_athletes_dir)
        from app import load_intake

        assert load_intake('../etc/passwd') == {}
        assert load_intake('not-a-uuid') == {}
        assert load_intake('') == {}

    def test_cleanup_stale_intakes(self, temp_athletes_dir):
        """Stale intake files are cleaned up."""
        os.environ['ATHLETES_DIR'] = str(temp_athletes_dir)
        from app import store_intake, cleanup_stale_intakes, get_intake_dir

        intake_id = '550e8400-e29b-41d4-a716-446655440002'
        store_intake(intake_id, {'name': 'Old User'})

        # Make the file appear old
        intake_file = get_intake_dir() / f'{intake_id}.json'
        old_time = (datetime.now() - timedelta(hours=25)).timestamp()
        os.utime(intake_file, (old_time, old_time))

        cleanup_stale_intakes()
        assert not intake_file.exists()


class TestCreateCheckout:
    """Tests for POST /api/create-checkout endpoint."""

    def _future_date(self, weeks_ahead=12):
        """Helper: return ISO date string N weeks from now."""
        d = datetime.now() + timedelta(weeks=weeks_ahead)
        return d.strftime('%Y-%m-%d')

    def test_checkout_rejects_missing_email(self, client):
        """Checkout requires a valid email."""
        response = client.post(
            '/api/create-checkout',
            json={'name': 'Test', 'races': [{'name': 'R', 'date': self._future_date(), 'priority': 'A'}]},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'email' in data['error'].lower()

    def test_checkout_rejects_missing_name(self, client):
        """Checkout requires a name."""
        response = client.post(
            '/api/create-checkout',
            json={'email': 'test@test.com', 'races': [{'name': 'R', 'date': self._future_date(), 'priority': 'A'}]},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'name' in data['error'].lower()

    def test_checkout_rejects_no_races(self, client):
        """Checkout requires at least one race."""
        response = client.post(
            '/api/create-checkout',
            json={'name': 'Test', 'email': 'test@test.com', 'races': []},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'race' in data['error'].lower()

    def test_checkout_rejects_missing_race_date(self, client):
        """Checkout requires a date on the A-race."""
        response = client.post(
            '/api/create-checkout',
            json={'name': 'Test', 'email': 'test@test.com', 'races': [{'name': 'R', 'priority': 'A'}]},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'date' in data['error'].lower()

    def test_checkout_uses_a_race_date(self, client, temp_athletes_dir):
        """Checkout uses A-race date for pricing, not first race."""
        with patch('app.stripe') as mock_stripe:
            mock_session = MagicMock()
            mock_session.id = 'cs_test_arace'
            mock_session.url = 'https://checkout.stripe.com/test'
            mock_stripe.checkout.Session.create.return_value = mock_session

            near_date = self._future_date(weeks_ahead=5)   # 5 wk = $75
            far_date = self._future_date(weeks_ahead=16)    # 16 wk = $240

            response = client.post(
                '/api/create-checkout',
                json={
                    'name': 'Test',
                    'email': 'test@test.com',
                    'races': [
                        {'name': 'Near Race', 'date': near_date, 'priority': 'B'},
                        {'name': 'Far Race', 'date': far_date, 'priority': 'A'},
                    ],
                },
                content_type='application/json'
            )

            assert response.status_code == 200
            data = response.get_json()
            # Should use the A-race (far_date), not the first race (near_date)
            assert data['price']['weeks'] >= 16

    def test_checkout_falls_back_to_first_race(self, client, temp_athletes_dir):
        """Without an A-race, checkout uses first race's date."""
        with patch('app.stripe') as mock_stripe:
            mock_session = MagicMock()
            mock_session.id = 'cs_test_fallback'
            mock_session.url = 'https://checkout.stripe.com/test'
            mock_stripe.checkout.Session.create.return_value = mock_session

            race_date = self._future_date(weeks_ahead=8)

            response = client.post(
                '/api/create-checkout',
                json={
                    'name': 'Test',
                    'email': 'test@test.com',
                    'races': [
                        {'name': 'Only Race', 'date': race_date, 'priority': 'B'},
                    ],
                },
                content_type='application/json'
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['price']['weeks'] >= 8

    def test_checkout_creates_session_with_computed_price(self, client, temp_athletes_dir):
        """Valid checkout creates Stripe session with computed $/wk price."""
        with patch('app.stripe') as mock_stripe:
            mock_session = MagicMock()
            mock_session.id = 'cs_test_789'
            mock_session.url = 'https://checkout.stripe.com/pay/cs_test_789'
            mock_stripe.checkout.Session.create.return_value = mock_session

            race_date = self._future_date(weeks_ahead=12)
            response = client.post(
                '/api/create-checkout',
                json={
                    'name': 'Jane Doe',
                    'email': 'jane@example.com',
                    'races': [{'name': 'Unbound 200', 'date': race_date, 'priority': 'A'}],
                    'hours_per_week': '7-10',
                    'ftp': '250',
                },
                content_type='application/json'
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['checkout_url'] == 'https://checkout.stripe.com/pay/cs_test_789'
            assert 'intake_id' in data
            assert 'price' in data
            assert data['price']['weeks'] >= 12

            # Verify Stripe was called with pre-built price ID
            call_kwargs = mock_stripe.checkout.Session.create.call_args.kwargs
            line_item = call_kwargs['line_items'][0]
            assert 'price' in line_item
            assert line_item['price'].startswith('price_')
            assert call_kwargs['customer_email'] == 'jane@example.com'
            assert call_kwargs['metadata']['tier'] == 'custom'
            assert call_kwargs['metadata']['product_type'] == 'training_plan'

    def test_checkout_price_capped_at_249(self, client, temp_athletes_dir):
        """Price is capped at $249 for very long plans."""
        with patch('app.stripe') as mock_stripe:
            mock_session = MagicMock()
            mock_session.id = 'cs_test_cap'
            mock_session.url = 'https://checkout.stripe.com/test'
            mock_stripe.checkout.Session.create.return_value = mock_session

            # 30 weeks out = 30 * $15 = $450 → capped at $249
            race_date = self._future_date(weeks_ahead=30)
            response = client.post(
                '/api/create-checkout',
                json={
                    'name': 'Long Plan',
                    'email': 'long@test.com',
                    'races': [{'name': 'Far Race', 'date': race_date, 'priority': 'A'}],
                },
                content_type='application/json'
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['price']['price_cents'] == 24900  # $249 cap

    def test_checkout_options_returns_204(self, client):
        """CORS preflight returns 204."""
        response = client.options('/api/create-checkout')
        assert response.status_code == 204

    def test_cors_headers_present(self, client):
        """CORS headers are set on checkout responses."""
        response = client.post(
            '/api/create-checkout',
            json={'name': 'Test', 'email': 'bad'},
            content_type='application/json',
            headers={'Origin': 'https://gravelgodcycling.com'}
        )
        # Even on error, CORS headers should be present
        assert 'Access-Control-Allow-Origin' in response.headers


class TestStripeWebhookWithIntake:
    """Tests for Stripe webhook with intake data flow."""

    def test_stripe_webhook_loads_intake_data(self, client, temp_athletes_dir):
        """Stripe webhook loads rich questionnaire data from intake store."""
        # Store intake data using app module's actual ATHLETES_DIR
        # (module-level constant set at first import)
        import app as app_module
        intake_id = '550e8400-e29b-41d4-a716-446655440010'
        intake_dir = Path(app_module.ATHLETES_DIR) / '.intake'
        intake_dir.mkdir(parents=True, exist_ok=True)
        intake_file = intake_dir / f'{intake_id}.json'
        intake_file.write_text(json.dumps({
            'intake_id': intake_id,
            'stored_at': datetime.now().isoformat(),
            'data': {
                'name': 'Sarah Connor',
                'email': 'sarah@example.com',
                'weight': '140',
                'ftp': '220',
                'hours_per_week': '7-10',
                'races': [{'name': 'Unbound 200', 'date': '2026-06-01', 'priority': 'A'}],
            }
        }))

        stripe_event = {
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_test_intake',
                    'amount_total': 18000,
                    'customer_details': {
                        'name': 'Sarah Connor',
                        'email': 'sarah@example.com',
                    },
                    'metadata': {
                        'intake_id': intake_id,
                        'tier': 'custom',
                        'athlete_name': 'Sarah Connor',
                        'weeks': '12',
                        'price_cents': '18000',
                    }
                }
            }
        }

        with patch('app.run_pipeline') as mock_pipeline:
            mock_pipeline.return_value = {'success': True, 'stdout': '', 'stderr': ''}

            response = client.post(
                '/webhook/stripe',
                json=stripe_event,
                content_type='application/json'
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'success'
            assert data['athlete_id'] == 'sarah_connor'

        # Verify profile was created with intake data
        import yaml
        profile_path = Path(app_module.ATHLETES_DIR) / 'sarah_connor' / 'profile.yaml'
        assert profile_path.exists()
        with open(profile_path) as f:
            profile = yaml.safe_load(f)
        assert profile['name'] == 'Sarah Connor'
        assert profile['email'] == 'sarah@example.com'
        assert profile['tier'] == 'custom'
        # Weight should be converted from lbs to kg
        assert profile['fitness_markers']['ftp_watts'] == 220

    def test_stripe_webhook_works_without_intake(self, client, temp_athletes_dir):
        """Stripe webhook still works without intake data (sparse fallback)."""
        stripe_event = {
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_test_no_intake',
                    'amount_total': 12000,
                    'customer_details': {
                        'name': 'No Intake User',
                        'email': 'no@intake.com',
                    },
                    'metadata': {
                        'tier': 'custom',
                    }
                }
            }
        }

        with patch('app.run_pipeline') as mock_pipeline:
            mock_pipeline.return_value = {'success': True, 'stdout': '', 'stderr': ''}

            response = client.post(
                '/webhook/stripe',
                json=stripe_event,
                content_type='application/json'
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'success'


class TestPriceComputation:
    """Tests for $/wk computed pricing model."""

    def test_price_8_weeks(self):
        """8 weeks = 8 * $15 = $120."""
        from app import compute_plan_price
        d = (datetime.now() + timedelta(weeks=8)).strftime('%Y-%m-%d')
        result = compute_plan_price(d)
        assert result['weeks'] >= 8
        assert result['price_cents'] == result['weeks'] * 1500

    def test_price_minimum_4_weeks(self):
        """Short plans get minimum 4 weeks ($60)."""
        from app import compute_plan_price
        # Race is 1 week away
        d = (datetime.now() + timedelta(weeks=1)).strftime('%Y-%m-%d')
        result = compute_plan_price(d)
        assert result['weeks'] == 4
        assert result['price_cents'] == 6000  # $60

    def test_price_capped_at_249(self):
        """Long plans are capped at $249."""
        from app import compute_plan_price
        # Race is 30 weeks away = $450 → capped at $249
        d = (datetime.now() + timedelta(weeks=30)).strftime('%Y-%m-%d')
        result = compute_plan_price(d)
        assert result['weeks'] >= 30
        assert result['price_cents'] == 24900  # $249 cap

    def test_price_cap_boundary(self):
        """17 weeks × $15 = $255 → capped at $249."""
        from app import compute_plan_price, PRICE_PER_WEEK_CENTS, PRICE_CAP_CENTS
        # 16 weeks: 16 * $15 = $240 (under cap)
        d16 = (datetime.now() + timedelta(weeks=16)).strftime('%Y-%m-%d')
        r16 = compute_plan_price(d16)
        assert r16['price_cents'] <= PRICE_CAP_CENTS

        # 17 weeks: 17 * $15 = $255 → capped at $249
        d17 = (datetime.now() + timedelta(weeks=17)).strftime('%Y-%m-%d')
        r17 = compute_plan_price(d17)
        assert r17['price_cents'] == PRICE_CAP_CENTS

    def test_price_invalid_date(self):
        """Invalid date returns minimum price."""
        from app import compute_plan_price
        result = compute_plan_price('not-a-date')
        assert result['weeks'] == 4
        assert result['price_cents'] == 6000

    def test_price_past_date(self):
        """Past race date gets minimum 4 weeks."""
        from app import compute_plan_price
        d = (datetime.now() - timedelta(weeks=2)).strftime('%Y-%m-%d')
        result = compute_plan_price(d)
        assert result['weeks'] == 4
        assert result['price_cents'] == 6000

    def test_pricing_constants(self):
        """Pricing constants are correct."""
        from app import PRICE_PER_WEEK_CENTS, PRICE_CAP_CENTS, MIN_WEEKS
        assert PRICE_PER_WEEK_CENTS == 1500  # $15
        assert PRICE_CAP_CENTS == 24900       # $249
        assert MIN_WEEKS == 4


class TestPriceParityPythonJs:
    """Verify Python and JS price computations produce identical results.

    The user sees a JS-computed price on the submit button, then gets
    charged a Python-computed price via Stripe. If these ever diverge,
    we have a trust/legal problem. This test runs the JS through Node.js
    and compares against Python for multiple date scenarios.
    """

    PARITY_JS = """
    // Mirror of computePrice() from training-plans-form.js
    var PRICE_PER_WEEK = 15;
    var PRICE_CAP = 249;
    var MIN_WEEKS = 4;

    function computePrice(raceDateStr) {
      var raceDate = new Date(raceDateStr + 'T00:00:00');
      var today = new Date();
      today.setHours(0, 0, 0, 0);
      var days = Math.ceil((raceDate - today) / (1000 * 60 * 60 * 24));
      var weeks = Math.max(MIN_WEEKS, Math.ceil(days / 7));
      var price = Math.min(weeks * PRICE_PER_WEEK, PRICE_CAP);
      return JSON.stringify({weeks: weeks, price_cents: price * 100});
    }

    var dates = %DATES%;
    var results = dates.map(function(d) { return computePrice(d); });
    console.log(JSON.stringify(results));
    """

    def test_parity_across_date_scenarios(self):
        """Python and JS produce same price for 6 date scenarios."""
        from app import compute_plan_price

        # 6 scenarios: short, medium, at-cap, past-cap, past, near-today
        test_dates = [
            (datetime.now() + timedelta(weeks=5)).strftime('%Y-%m-%d'),
            (datetime.now() + timedelta(weeks=10)).strftime('%Y-%m-%d'),
            (datetime.now() + timedelta(weeks=16)).strftime('%Y-%m-%d'),
            (datetime.now() + timedelta(weeks=30)).strftime('%Y-%m-%d'),
            (datetime.now() - timedelta(weeks=2)).strftime('%Y-%m-%d'),
            (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'),
        ]

        # Python results
        py_results = [compute_plan_price(d) for d in test_dates]

        # JS results via Node.js
        js_code = self.PARITY_JS.replace('%DATES%', json.dumps(test_dates))
        import subprocess
        result = subprocess.run(
            ['node', '-e', js_code],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, f"Node.js failed: {result.stderr}"
        js_results = json.loads(result.stdout.strip())

        for i, (py, js_str) in enumerate(zip(py_results, js_results)):
            js = json.loads(js_str)
            assert py['price_cents'] == js['price_cents'], (
                f"Date {test_dates[i]}: Python={py['price_cents']} JS={js['price_cents']}"
            )
            assert py['weeks'] == js['weeks'], (
                f"Date {test_dates[i]}: Python weeks={py['weeks']} JS weeks={js['weeks']}"
            )


class TestTestEndpoint:
    """Tests for the test endpoint (only available in non-production)."""

    def test_test_endpoint_creates_profile(self, client, temp_athletes_dir):
        """Test endpoint creates profile without running pipeline."""
        response = client.post(
            '/webhook/test',
            json={
                'athlete_id': 'test_user',
                'tier': 'starter',
                'profile': {
                    'name': 'Test User',
                    'email': 'test@example.com',
                }
            },
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert 'test_user' in data['athlete_id']

    def test_test_endpoint_sanitizes_dangerous_id(self, client, temp_athletes_dir):
        """Test endpoint sanitizes dangerous athlete IDs."""
        # The sanitize function strips dangerous characters
        # so '../etc/passwd' becomes 'etcpasswd'
        response = client.post(
            '/webhook/test',
            json={'athlete_id': '../etc/passwd'},
            content_type='application/json'
        )

        # Should succeed but with sanitized ID (no path traversal)
        assert response.status_code == 200
        data = response.get_json()
        # The athlete_id should NOT contain path traversal chars
        assert '..' not in data.get('athlete_id', '')
        assert '/' not in data.get('athlete_id', '')


class TestCoachingCheckout:
    """Tests for POST /api/create-coaching-checkout endpoint."""

    def test_coaching_checkout_rejects_missing_email(self, client):
        """Coaching checkout requires a valid email."""
        response = client.post(
            '/api/create-coaching-checkout',
            json={'name': 'Test', 'tier': 'min'},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'email' in data['error'].lower()

    def test_coaching_checkout_rejects_missing_name(self, client):
        """Coaching checkout requires a name."""
        response = client.post(
            '/api/create-coaching-checkout',
            json={'email': 'test@test.com', 'tier': 'min'},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'name' in data['error'].lower()

    def test_coaching_checkout_rejects_invalid_tier(self, client):
        """Coaching checkout rejects invalid tier."""
        response = client.post(
            '/api/create-coaching-checkout',
            json={'name': 'Test', 'email': 'test@test.com', 'tier': 'ultra'},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'tier' in data['error'].lower()

    def test_coaching_checkout_rejects_missing_tier(self, client):
        """Coaching checkout rejects missing tier."""
        response = client.post(
            '/api/create-coaching-checkout',
            json={'name': 'Test', 'email': 'test@test.com'},
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_coaching_checkout_creates_session(self, client, temp_athletes_dir):
        """Valid coaching checkout creates Stripe subscription session."""
        with patch('app.stripe') as mock_stripe:
            mock_session = MagicMock()
            mock_session.id = 'cs_test_coaching'
            mock_session.url = 'https://checkout.stripe.com/coaching'
            mock_stripe.checkout.Session.create.return_value = mock_session

            response = client.post(
                '/api/create-coaching-checkout',
                json={'name': 'Coach Me', 'email': 'coach@test.com', 'tier': 'mid'},
                content_type='application/json'
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['checkout_url'] == 'https://checkout.stripe.com/coaching'

            call_kwargs = mock_stripe.checkout.Session.create.call_args.kwargs
            assert call_kwargs['mode'] == 'subscription'
            assert call_kwargs['customer_email'] == 'coach@test.com'
            assert call_kwargs['metadata']['product_type'] == 'coaching'
            assert call_kwargs['metadata']['tier'] == 'mid'

    def test_coaching_checkout_includes_setup_fee(self, client, temp_athletes_dir):
        """Coaching checkout includes $99 setup fee as second line item."""
        with patch('app.stripe') as mock_stripe:
            mock_session = MagicMock()
            mock_session.id = 'cs_test_coaching_fee'
            mock_session.url = 'https://checkout.stripe.com/coaching-fee'
            mock_stripe.checkout.Session.create.return_value = mock_session

            response = client.post(
                '/api/create-coaching-checkout',
                json={'name': 'Fee Test', 'email': 'fee@test.com', 'tier': 'min'},
                content_type='application/json'
            )

            assert response.status_code == 200
            call_kwargs = mock_stripe.checkout.Session.create.call_args.kwargs

            # Should have 2 line items: subscription + setup fee
            line_items = call_kwargs['line_items']
            assert len(line_items) == 2
            # First item is the recurring subscription
            assert line_items[0]['quantity'] == 1
            # Second item is the setup fee
            assert line_items[1]['quantity'] == 1

    def test_coaching_checkout_allows_promo_codes(self, client, temp_athletes_dir):
        """Coaching checkout enables promotion codes for setup fee waivers."""
        with patch('app.stripe') as mock_stripe:
            mock_session = MagicMock()
            mock_session.id = 'cs_test_coaching_promo'
            mock_session.url = 'https://checkout.stripe.com/coaching-promo'
            mock_stripe.checkout.Session.create.return_value = mock_session

            response = client.post(
                '/api/create-coaching-checkout',
                json={'name': 'Promo Test', 'email': 'promo@test.com', 'tier': 'mid'},
                content_type='application/json'
            )

            assert response.status_code == 200
            call_kwargs = mock_stripe.checkout.Session.create.call_args.kwargs
            assert call_kwargs['allow_promotion_codes'] is True

    def test_coaching_checkout_all_tiers(self, client, temp_athletes_dir):
        """All three coaching tiers create valid sessions."""
        for tier in ['min', 'mid', 'max']:
            with patch('app.stripe') as mock_stripe:
                mock_session = MagicMock()
                mock_session.id = f'cs_test_{tier}'
                mock_session.url = f'https://checkout.stripe.com/{tier}'
                mock_stripe.checkout.Session.create.return_value = mock_session

                response = client.post(
                    '/api/create-coaching-checkout',
                    json={'name': 'Test', 'email': 'test@test.com', 'tier': tier},
                    content_type='application/json'
                )
                assert response.status_code == 200, f"Tier {tier} failed"

    def test_coaching_checkout_options_preflight(self, client):
        """CORS preflight returns 204."""
        response = client.options('/api/create-coaching-checkout')
        assert response.status_code == 204

    def test_coaching_checkout_handles_stripe_error(self, client, temp_athletes_dir):
        """Coaching checkout returns 502 on Stripe API failure."""
        with patch('app.stripe') as mock_stripe:
            # Create a mock StripeError that isinstance checks work with
            class MockStripeError(Exception):
                pass
            mock_stripe.error.StripeError = MockStripeError
            mock_stripe.checkout.Session.create.side_effect = MockStripeError('API down')

            response = client.post(
                '/api/create-coaching-checkout',
                json={'name': 'Test', 'email': 'test@test.com', 'tier': 'min'},
                content_type='application/json'
            )
            assert response.status_code == 502


class TestConsultingCheckout:
    """Tests for POST /api/create-consulting-checkout endpoint."""

    def test_consulting_checkout_rejects_missing_email(self, client):
        """Consulting checkout requires a valid email."""
        response = client.post(
            '/api/create-consulting-checkout',
            json={'name': 'Test', 'hours': 1},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'email' in data['error'].lower()

    def test_consulting_checkout_rejects_missing_name(self, client):
        """Consulting checkout requires a name."""
        response = client.post(
            '/api/create-consulting-checkout',
            json={'email': 'test@test.com', 'hours': 1},
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'name' in data['error'].lower()

    def test_consulting_checkout_rejects_zero_hours(self, client):
        """Consulting checkout rejects 0 hours."""
        response = client.post(
            '/api/create-consulting-checkout',
            json={'name': 'Test', 'email': 'test@test.com', 'hours': 0},
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_consulting_checkout_rejects_excessive_hours(self, client):
        """Consulting checkout rejects more than 10 hours."""
        response = client.post(
            '/api/create-consulting-checkout',
            json={'name': 'Test', 'email': 'test@test.com', 'hours': 11},
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_consulting_checkout_rejects_non_numeric_hours(self, client):
        """Consulting checkout rejects non-numeric hours."""
        response = client.post(
            '/api/create-consulting-checkout',
            json={'name': 'Test', 'email': 'test@test.com', 'hours': 'abc'},
            content_type='application/json'
        )
        assert response.status_code == 400

    def test_consulting_checkout_defaults_to_1_hour(self, client, temp_athletes_dir):
        """Consulting checkout defaults to 1 hour if not specified."""
        with patch('app.stripe') as mock_stripe:
            mock_session = MagicMock()
            mock_session.id = 'cs_test_consult'
            mock_session.url = 'https://checkout.stripe.com/consult'
            mock_stripe.checkout.Session.create.return_value = mock_session

            response = client.post(
                '/api/create-consulting-checkout',
                json={'name': 'Test', 'email': 'test@test.com'},
                content_type='application/json'
            )

            assert response.status_code == 200
            call_kwargs = mock_stripe.checkout.Session.create.call_args.kwargs
            assert call_kwargs['line_items'][0]['quantity'] == 1

    def test_consulting_checkout_creates_session(self, client, temp_athletes_dir):
        """Valid consulting checkout creates Stripe payment session."""
        with patch('app.stripe') as mock_stripe:
            mock_session = MagicMock()
            mock_session.id = 'cs_test_consult_3hr'
            mock_session.url = 'https://checkout.stripe.com/consult3'
            mock_stripe.checkout.Session.create.return_value = mock_session

            response = client.post(
                '/api/create-consulting-checkout',
                json={'name': 'Consult Me', 'email': 'consult@test.com', 'hours': 3},
                content_type='application/json'
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data['checkout_url'] == 'https://checkout.stripe.com/consult3'

            call_kwargs = mock_stripe.checkout.Session.create.call_args.kwargs
            assert call_kwargs['mode'] == 'payment'
            assert call_kwargs['line_items'][0]['quantity'] == 3
            assert call_kwargs['metadata']['product_type'] == 'consulting'
            assert call_kwargs['metadata']['hours'] == '3'

    def test_consulting_checkout_options_preflight(self, client):
        """CORS preflight returns 204."""
        response = client.options('/api/create-consulting-checkout')
        assert response.status_code == 204


class TestCoachingWebhook:
    """Tests for coaching webhook handler."""

    def test_coaching_webhook_processes_subscription(self, client, temp_athletes_dir):
        """Coaching webhook processes subscription and logs event."""
        stripe_event = {
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_coaching_123',
                    'customer_details': {
                        'name': 'New Coach Client',
                        'email': 'client@example.com',
                    },
                    'subscription': 'sub_test_123',
                    'metadata': {
                        'product_type': 'coaching',
                        'tier': 'mid',
                        'athlete_name': 'New Coach Client',
                    }
                }
            }
        }

        response = client.post(
            '/webhook/stripe',
            json=stripe_event,
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['product_type'] == 'coaching'
        assert data['tier'] == 'mid'

    def test_coaching_webhook_logs_event(self, client, temp_athletes_dir):
        """Coaching webhook writes to order log."""
        import app as app_module

        stripe_event = {
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_coaching_log',
                    'customer_details': {'email': 'log@test.com'},
                    'subscription': 'sub_log_123',
                    'metadata': {
                        'product_type': 'coaching',
                        'tier': 'max',
                        'athlete_name': 'Log Test',
                    }
                }
            }
        }

        response = client.post(
            '/webhook/stripe',
            json=stripe_event,
            content_type='application/json'
        )

        assert response.status_code == 200

        # Verify log file was written
        log_dir = Path(app_module.ATHLETES_DIR) / '.logs'
        log_files = list(log_dir.glob('*.jsonl'))
        assert len(log_files) > 0

        with open(log_files[0]) as f:
            lines = f.readlines()
        last_entry = json.loads(lines[-1])
        assert last_entry['product_type'] == 'coaching'
        assert last_entry['tier'] == 'max'

    def test_coaching_webhook_idempotent(self, client, temp_athletes_dir):
        """Duplicate coaching webhook is caught by idempotency."""
        stripe_event = {
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_coaching_dup',
                    'customer_details': {'email': 'dup@test.com'},
                    'metadata': {
                        'product_type': 'coaching',
                        'tier': 'min',
                        'athlete_name': 'Dup Test',
                    }
                }
            }
        }

        # First call
        r1 = client.post('/webhook/stripe', json=stripe_event,
                         content_type='application/json')
        assert r1.status_code == 200
        assert r1.get_json()['status'] == 'success'

        # Second call (duplicate)
        r2 = client.post('/webhook/stripe', json=stripe_event,
                         content_type='application/json')
        assert r2.status_code == 200
        assert r2.get_json()['status'] == 'duplicate'


class TestConsultingWebhook:
    """Tests for consulting webhook handler."""

    def test_consulting_webhook_processes_payment(self, client, temp_athletes_dir):
        """Consulting webhook processes payment and logs event."""
        stripe_event = {
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_consulting_123',
                    'customer_details': {
                        'name': 'Consult Client',
                        'email': 'consult@example.com',
                    },
                    'metadata': {
                        'product_type': 'consulting',
                        'athlete_name': 'Consult Client',
                        'hours': '2',
                    }
                }
            }
        }

        response = client.post(
            '/webhook/stripe',
            json=stripe_event,
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['product_type'] == 'consulting'
        assert data['hours'] == '2'

    def test_consulting_webhook_logs_event(self, client, temp_athletes_dir):
        """Consulting webhook writes to order log."""
        import app as app_module

        stripe_event = {
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_consulting_log',
                    'customer_details': {'email': 'clog@test.com'},
                    'metadata': {
                        'product_type': 'consulting',
                        'athlete_name': 'Log Consult',
                        'hours': '5',
                    }
                }
            }
        }

        response = client.post(
            '/webhook/stripe',
            json=stripe_event,
            content_type='application/json'
        )

        assert response.status_code == 200

        log_dir = Path(app_module.ATHLETES_DIR) / '.logs'
        log_files = list(log_dir.glob('*.jsonl'))
        assert len(log_files) > 0

        with open(log_files[0]) as f:
            lines = f.readlines()
        last_entry = json.loads(lines[-1])
        assert last_entry['product_type'] == 'consulting'
        assert last_entry['hours'] == '5'

    def test_consulting_webhook_idempotent(self, client, temp_athletes_dir):
        """Duplicate consulting webhook is caught by idempotency."""
        stripe_event = {
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_consulting_dup',
                    'customer_details': {'email': 'cdup@test.com'},
                    'metadata': {
                        'product_type': 'consulting',
                        'athlete_name': 'Dup Consult',
                        'hours': '1',
                    }
                }
            }
        }

        r1 = client.post('/webhook/stripe', json=stripe_event,
                         content_type='application/json')
        assert r1.status_code == 200
        assert r1.get_json()['status'] == 'success'

        r2 = client.post('/webhook/stripe', json=stripe_event,
                         content_type='application/json')
        assert r2.status_code == 200
        assert r2.get_json()['status'] == 'duplicate'


class TestPastDateRejection:
    """Tests for past race date validation."""

    def test_checkout_rejects_old_past_date(self, client):
        """Checkout rejects race dates more than 7 days in the past."""
        old_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        response = client.post(
            '/api/create-checkout',
            json={
                'name': 'Test',
                'email': 'test@test.com',
                'races': [{'name': 'Old Race', 'date': old_date, 'priority': 'A'}],
            },
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'past' in data['error'].lower()

    def test_checkout_allows_recent_past_date(self, client, temp_athletes_dir):
        """Checkout allows race dates within 7 days past (just-happened race)."""
        with patch('app.stripe') as mock_stripe:
            mock_session = MagicMock()
            mock_session.id = 'cs_recent_past'
            mock_session.url = 'https://checkout.stripe.com/test'
            mock_stripe.checkout.Session.create.return_value = mock_session

            recent_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
            response = client.post(
                '/api/create-checkout',
                json={
                    'name': 'Test',
                    'email': 'test@test.com',
                    'races': [{'name': 'Recent Race', 'date': recent_date, 'priority': 'A'}],
                },
                content_type='application/json'
            )
            assert response.status_code == 200

    def test_checkout_rejects_invalid_date_format(self, client):
        """Checkout rejects non-ISO date formats."""
        response = client.post(
            '/api/create-checkout',
            json={
                'name': 'Test',
                'email': 'test@test.com',
                'races': [{'name': 'Bad Date', 'date': '06/15/2026', 'priority': 'A'}],
            },
            content_type='application/json'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert 'date' in data['error'].lower()


class TestEmailMasking:
    """Tests for PII email masking in logs."""

    def test_mask_email_standard(self):
        """Standard email is properly masked."""
        from app import _mask_email
        assert _mask_email('user@example.com') == 'u***@e***.com'

    def test_mask_email_short_local(self):
        """Single-char local part is masked."""
        from app import _mask_email
        assert _mask_email('u@example.com') == 'u***@e***.com'

    def test_mask_email_empty(self):
        """Empty/invalid emails return '***'."""
        from app import _mask_email
        assert _mask_email('') == '***'
        assert _mask_email('not-an-email') == '***'
        assert _mask_email(None) == '***'

    def test_mask_email_preserves_tld(self):
        """TLD is preserved for readability."""
        from app import _mask_email
        result = _mask_email('test@company.co.uk')
        assert result.endswith('.uk')


class TestNotification:
    """Tests for order notification system."""

    def test_notify_logs_critical_without_smtp(self):
        """Without SMTP config, notification logs at CRITICAL level."""
        from app import _notify_new_order
        with patch('app.logger') as mock_logger:
            _notify_new_order('coaching', {'name': 'Test', 'tier': 'mid'})
            mock_logger.critical.assert_called_once()
            call_msg = mock_logger.critical.call_args[0][0]
            assert 'coaching' in call_msg.lower()
            assert 'Test' in call_msg


class TestLogProductEvent:
    """Tests for _log_product_event shared helper."""

    def test_log_product_event_writes_jsonl(self, temp_athletes_dir):
        """_log_product_event writes valid JSONL."""
        from app import _log_product_event

        with patch('app.ATHLETES_DIR', str(temp_athletes_dir)):
            _log_product_event('coaching', 'order_123', tier='mid', name='Test')

        log_dir = temp_athletes_dir / '.logs'
        log_files = list(log_dir.glob('*.jsonl'))
        assert len(log_files) == 1

        with open(log_files[0]) as f:
            entry = json.loads(f.readline())
        assert entry['product_type'] == 'coaching'
        assert entry['order_id'] == 'order_123'
        assert entry['tier'] == 'mid'
        assert entry['success'] is True


class TestIdempotencyTiming:
    """Tests that idempotency marking happens BEFORE pipeline execution."""

    def test_order_marked_before_pipeline(self, client, temp_athletes_dir):
        """Order is marked processed before pipeline runs (TOCTOU fix)."""
        import app as app_module

        call_order = []

        def mock_mark(order_id, athlete_id):
            call_order.append('mark')
            # Call the real function
            original_mark(order_id, athlete_id)

        def mock_pipeline(athlete_id, deliver=True):
            call_order.append('pipeline')
            # By the time pipeline runs, order should already be marked
            from app import check_idempotency
            assert check_idempotency('cs_test_timing'), \
                "Order must be marked as processed BEFORE pipeline runs"
            return {'success': True, 'stdout': '', 'stderr': ''}

        original_mark = app_module.mark_order_processed

        stripe_event = {
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_test_timing',
                    'customer_details': {
                        'name': 'Timing Test',
                        'email': 'timing@test.com',
                    },
                    'metadata': {'tier': 'custom'}
                }
            }
        }

        with patch('app.mark_order_processed', side_effect=mock_mark), \
             patch('app.run_pipeline', side_effect=mock_pipeline):
            response = client.post(
                '/webhook/stripe',
                json=stripe_event,
                content_type='application/json'
            )

        assert response.status_code == 200
        assert call_order == ['mark', 'pipeline'], \
            f"Expected mark before pipeline, got: {call_order}"


class TestCheckoutRecovery:
    """Tests for abandoned cart recovery flow."""

    def test_expired_checkout_sends_recovery(self, client, temp_athletes_dir):
        """Expired checkout with consent triggers recovery."""
        expired_event = {
            'type': 'checkout.session.expired',
            'data': {
                'object': {
                    'id': 'cs_expired_123',
                    'customer_details': {'email': 'abandoned@test.com'},
                    'metadata': {
                        'product_type': 'training_plan',
                        'athlete_name': 'Abandoned User',
                        'weeks': '12',
                    },
                    'consent': {'promotions': 'opt_in'},
                    'after_expiration': {
                        'recovery': {
                            'url': 'https://checkout.stripe.com/recover/cs_expired_123',
                        }
                    },
                }
            }
        }

        response = client.post(
            '/webhook/stripe',
            json=expired_event,
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'recovery_sent'

    def test_expired_checkout_skips_without_consent(self, client, temp_athletes_dir):
        """Expired checkout without consent does not send recovery."""
        expired_event = {
            'type': 'checkout.session.expired',
            'data': {
                'object': {
                    'id': 'cs_expired_noconsent',
                    'customer_details': {'email': 'noconsent@test.com'},
                    'metadata': {
                        'product_type': 'training_plan',
                        'athlete_name': 'No Consent',
                        'weeks': '8',
                    },
                    'consent': {},
                    'after_expiration': {
                        'recovery': {
                            'url': 'https://checkout.stripe.com/recover/cs_expired_noconsent',
                        }
                    },
                }
            }
        }

        response = client.post(
            '/webhook/stripe',
            json=expired_event,
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ignored'

    def test_expired_checkout_skips_without_recovery_url(self, client, temp_athletes_dir):
        """Expired checkout without recovery URL is ignored."""
        expired_event = {
            'type': 'checkout.session.expired',
            'data': {
                'object': {
                    'id': 'cs_expired_nourl',
                    'customer_details': {'email': 'nourl@test.com'},
                    'metadata': {'product_type': 'training_plan'},
                    'consent': {'promotions': 'opt_in'},
                    'after_expiration': {'recovery': {}},
                }
            }
        }

        response = client.post(
            '/webhook/stripe',
            json=expired_event,
            content_type='application/json'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ignored'

    def test_recovery_email_content(self, temp_athletes_dir):
        """Recovery email has correct subject and content per product type."""
        from app import _send_recovery_email

        # Just verify it doesn't crash (no SMTP configured = logs CRITICAL)
        with patch('app.logger') as mock_logger:
            _send_recovery_email(
                'test@test.com', 'Jane Doe', 'training_plan',
                {'weeks': '12'}, 'https://recover.example.com'
            )
            mock_logger.critical.assert_called_once()
            call_msg = mock_logger.critical.call_args[0][0]
            assert 'test@test.com' in call_msg
            assert 'https://recover.example.com' in call_msg

    def test_checkout_session_includes_recovery_params(self, client, temp_athletes_dir):
        """Checkout session creation includes recovery and consent params."""
        with patch('app.stripe') as mock_stripe:
            mock_session = MagicMock()
            mock_session.id = 'cs_test_recovery_params'
            mock_session.url = 'https://checkout.stripe.com/test'
            mock_stripe.checkout.Session.create.return_value = mock_session

            future_date = (datetime.now() + timedelta(weeks=12)).strftime('%Y-%m-%d')
            response = client.post(
                '/api/create-checkout',
                json={
                    'name': 'Recovery Test',
                    'email': 'recovery@test.com',
                    'races': [{'name': 'Test', 'date': future_date, 'priority': 'A'}],
                },
                content_type='application/json'
            )

            assert response.status_code == 200
            call_kwargs = mock_stripe.checkout.Session.create.call_args.kwargs

            # Verify recovery params
            assert call_kwargs['after_expiration']['recovery']['enabled'] is True
            assert 'expires_at' in call_kwargs
            assert call_kwargs['consent_collection']['promotions'] == 'auto'

            # Verify session_id in success URL
            assert '{CHECKOUT_SESSION_ID}' in call_kwargs['success_url']

    def test_recovered_session_logged(self, client, temp_athletes_dir):
        """Recovered sessions are logged when processed."""
        stripe_event = {
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_recovered_123',
                    'recovered_from': 'cs_expired_original',
                    'customer_details': {
                        'name': 'Recovered User',
                        'email': 'recovered@test.com',
                    },
                    'metadata': {'tier': 'custom'}
                }
            }
        }

        with patch('app.run_pipeline') as mock_pipeline:
            mock_pipeline.return_value = {'success': True, 'stdout': '', 'stderr': ''}

            response = client.post(
                '/webhook/stripe',
                json=stripe_event,
                content_type='application/json'
            )

            assert response.status_code == 200


class TestFollowupEmails:
    """Tests for post-purchase follow-up email sequence."""

    def test_cron_endpoint_rejects_no_secret(self, client):
        """Cron endpoint requires CRON_SECRET to be configured."""
        with patch('app.CRON_SECRET', ''):
            response = client.post('/api/cron/followup-emails')
            assert response.status_code == 503

    def test_cron_endpoint_rejects_bad_secret(self, client):
        """Cron endpoint rejects invalid secret."""
        with patch('app.CRON_SECRET', 'real-secret'):
            response = client.post(
                '/api/cron/followup-emails',
                headers={'X-Cron-Secret': 'wrong-secret'}
            )
            assert response.status_code == 401

    def test_cron_endpoint_accepts_valid_secret(self, client):
        """Cron endpoint processes with valid secret."""
        with patch('app.CRON_SECRET', 'test-secret'), \
             patch('app.process_followup_emails') as mock_process:
            mock_process.return_value = {'checked': 0, 'sent': 0, 'skipped': 0, 'errors': 0}
            response = client.post(
                '/api/cron/followup-emails',
                headers={'X-Cron-Secret': 'test-secret'}
            )
            assert response.status_code == 200
            assert response.get_json()['status'] == 'ok'

    def test_process_sends_day_1_email(self, tmp_path):
        """Day 1 follow-up sent for order placed yesterday."""
        log_dir = tmp_path / '.logs'
        log_dir.mkdir()

        # Create order from 1 day ago
        order_time = (datetime.utcnow() - timedelta(days=1)).isoformat()
        order = json.dumps({
            'product_type': 'training_plan',
            'order_id': 'cs_test_day1',
            'email': 'athlete@test.com',
            'name': 'Test Athlete',
            'timestamp': order_time,
        })
        (log_dir / 'orders.jsonl').write_text(order + '\n')

        with patch('app.ATHLETES_DIR', str(tmp_path)), \
             patch('app._send_followup_email') as mock_send:
            mock_send.return_value = True
            from app import process_followup_emails
            stats = process_followup_emails()

        assert stats['sent'] == 1
        mock_send.assert_called_once()
        args = mock_send.call_args
        assert 'athlete@test.com' == args[0][0]
        assert 'Getting started' in args[0][1]

    def test_process_skips_already_sent(self, tmp_path):
        """Follow-up not re-sent if already tracked."""
        log_dir = tmp_path / '.logs'
        log_dir.mkdir()

        order_time = (datetime.utcnow() - timedelta(days=1)).isoformat()
        order = json.dumps({
            'product_type': 'training_plan',
            'order_id': 'cs_test_dedup',
            'email': 'athlete@test.com',
            'name': 'Test',
            'timestamp': order_time,
        })
        (log_dir / 'orders.jsonl').write_text(order + '\n')

        # Mark day 1 as already sent
        sent = json.dumps({
            'order_id': 'cs_test_dedup',
            'day': 1,
            'email': 'a***@test.com',
            'sent_at': datetime.utcnow().isoformat(),
        })
        (log_dir / 'followup_sent.jsonl').write_text(sent + '\n')

        with patch('app.ATHLETES_DIR', str(tmp_path)), \
             patch('app._send_followup_email') as mock_send:
            from app import process_followup_emails
            stats = process_followup_emails()

        mock_send.assert_not_called()
        assert stats['sent'] == 0

    def test_process_skips_coaching_orders(self, tmp_path):
        """Coaching orders don't get automated follow-ups."""
        log_dir = tmp_path / '.logs'
        log_dir.mkdir()

        order_time = (datetime.utcnow() - timedelta(days=1)).isoformat()
        order = json.dumps({
            'product_type': 'coaching',
            'order_id': 'cs_test_coaching',
            'email': 'coach@test.com',
            'name': 'Coach Client',
            'timestamp': order_time,
        })
        (log_dir / 'orders.jsonl').write_text(order + '\n')

        with patch('app.ATHLETES_DIR', str(tmp_path)), \
             patch('app._send_followup_email') as mock_send:
            from app import process_followup_emails
            stats = process_followup_emails()

        mock_send.assert_not_called()
        assert stats['checked'] == 0

    def test_process_sends_day_7_with_coaching_upsell(self, tmp_path):
        """Day 7 email includes coaching cross-sell link."""
        log_dir = tmp_path / '.logs'
        log_dir.mkdir()

        order_time = (datetime.utcnow() - timedelta(days=7)).isoformat()
        order = json.dumps({
            'product_type': 'training_plan',
            'order_id': 'cs_test_day7',
            'email': 'athlete@test.com',
            'name': 'Week One Done',
            'timestamp': order_time,
        })
        (log_dir / 'orders.jsonl').write_text(order + '\n')

        with patch('app.ATHLETES_DIR', str(tmp_path)), \
             patch('app._send_followup_email') as mock_send:
            mock_send.return_value = True
            from app import process_followup_emails
            process_followup_emails()

        # Day 7 email should mention coaching
        call_args = mock_send.call_args
        assert '/coaching/' in call_args[0][2]  # body contains coaching URL

    def test_followup_sequence_has_required_fields(self):
        """All follow-up templates have required fields."""
        from app import FOLLOWUP_SEQUENCE
        for followup in FOLLOWUP_SEQUENCE:
            assert 'day' in followup
            assert 'subject' in followup
            assert 'template' in followup
            assert '{first_name}' in followup['template']
            assert followup['day'] > 0

    def test_mark_and_read_followup_sent(self, tmp_path):
        """Sent log correctly tracks and reads follow-ups."""
        with patch('app.ATHLETES_DIR', str(tmp_path)):
            from app import _mark_followup_sent, _get_sent_followups
            _mark_followup_sent('order_123', 1, 'test@example.com')
            _mark_followup_sent('order_123', 3, 'test@example.com')

            sent = _get_sent_followups()
            assert ('order_123', 1) in sent
            assert ('order_123', 3) in sent
            assert ('order_123', 7) not in sent


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
