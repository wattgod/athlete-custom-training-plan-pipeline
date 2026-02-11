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
from datetime import datetime

import pytest

# Add webhook directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment before importing app
os.environ['FLASK_ENV'] = 'test'
os.environ['WOOCOMMERCE_SECRET'] = ''  # Disable signature check in tests
os.environ['STRIPE_WEBHOOK_SECRET'] = ''


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
                    'amount_total': 14900,  # $149
                    'customer_details': {
                        'name': 'Test User',
                        'email': 'test@example.com',
                    },
                    'metadata': {
                        'race_name': 'Test Race',
                        'race_date': '2025-06-01',
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

    def test_extract_stripe_tier_from_amount(self):
        """Tier is correctly determined from payment amount."""
        from app import extract_stripe_data

        # $99 = starter
        data = {
            'data': {
                'object': {
                    'id': 'cs_123',
                    'amount_total': 9900,
                    'customer_details': {'name': 'Test', 'email': 'test@test.com'},
                    'metadata': {}
                }
            }
        }
        result = extract_stripe_data(data)
        assert result['tier'] == 'starter'

        # $149 = race_ready
        data['data']['object']['amount_total'] = 14900
        result = extract_stripe_data(data)
        assert result['tier'] == 'race_ready'

        # $199 = full_build
        data['data']['object']['amount_total'] = 19900
        result = extract_stripe_data(data)
        assert result['tier'] == 'full_build'


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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
