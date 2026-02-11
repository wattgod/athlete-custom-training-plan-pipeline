#!/usr/bin/env python3
"""
Tests for the Gravel God Web App.

Run with: pytest webapp/tests/test_webapp.py -v
"""

import os
import sys
from pathlib import Path

import pytest

# Set test environment before importing
os.environ['SECRET_KEY'] = 'test-secret-key-12345'
os.environ['FLASK_ENV'] = 'test'
os.environ['GG_API_KEY'] = ''
os.environ['GG_ADMIN_PASSWORD'] = ''

# Add webapp directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


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

        assert sanitize_athlete_id('John Doe') == 'john-doe'
        assert sanitize_athlete_id('Mary Jane Watson') == 'mary-jane-watson'
        assert sanitize_athlete_id('Test!!!User') == 'testuser'
        assert sanitize_athlete_id('  Spaces  ') == 'spaces'
        assert sanitize_athlete_id('') == ''


class TestFlaskApp:
    """Tests requiring Flask app context."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        from app import app
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_index_returns_200(self, client):
        """Index page returns 200."""
        response = client.get('/')
        assert response.status_code == 200

    def test_login_page_renders(self, client):
        """Login page renders correctly."""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'Login' in response.data or b'Password' in response.data

    def test_logout_redirects(self, client):
        """Logout clears session and redirects."""
        response = client.get('/logout')
        assert response.status_code == 302

    def test_security_headers_present(self, client):
        """Security headers are set on responses."""
        response = client.get('/')

        assert response.headers.get('X-Content-Type-Options') == 'nosniff'
        assert response.headers.get('X-Frame-Options') == 'DENY'
        assert response.headers.get('X-XSS-Protection') == '1; mode=block'

    def test_404_handler(self, client):
        """404 handler returns proper error page."""
        response = client.get('/nonexistent/route/12345')
        assert response.status_code == 404

    def test_path_traversal_blocked(self, client):
        """Path traversal attempts are blocked."""
        dangerous_ids = [
            '../etc/passwd',
            '..\\windows\\system32',
            'test/../../../etc/passwd',
        ]

        for dangerous_id in dangerous_ids:
            response = client.get(f'/athlete/{dangerous_id}')
            assert response.status_code in [400, 404]
            assert b'passwd' not in response.data

    def test_api_invalid_athlete_id(self, client):
        """API returns error for invalid ID."""
        response = client.get('/api/athlete/../etc/passwd')
        # Either 400 (invalid) or 404 (not found) is acceptable
        assert response.status_code in [400, 404]

    def test_api_invalid_step_name(self, client):
        """API returns 400 for invalid step name."""
        response = client.post('/api/athlete/test/step/malicious_script')
        assert response.status_code == 400

    def test_api_athletes_returns_json(self, client):
        """API returns JSON list."""
        response = client.get('/api/athletes')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)


class TestPipelineStepValidation:
    """Tests for pipeline step validation."""

    def test_allowed_scripts_only(self):
        """Only whitelisted scripts can run."""
        from app import run_pipeline_step

        # These should fail with "not allowed"
        success, output = run_pipeline_step('malicious.py', 'test')
        assert success is False
        assert 'not allowed' in output.lower()

        success, output = run_pipeline_step('../../../etc/passwd', 'test')
        assert success is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
