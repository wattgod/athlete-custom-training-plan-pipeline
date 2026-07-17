#!/usr/bin/env python3
"""
Configuration loader for Gravel God pipeline.

Loads settings from config.yaml with environment variable overrides.
"""

import os
import re
import threading
import yaml
from brand_config import brand_from_profile, get_brand_config, normalize_brand
from pathlib import Path
from typing import Any, Dict, Optional, Set


# Allowlist of environment variables that can be substituted
ALLOWED_ENV_VARS: Set[str] = {
    'GG_GUIDES_DIR',
    'ROADIE_GUIDES_DIR',
    'GG_BRAND_DIR',
    'GG_DELIVERY_DIR',
    'GG_DOWNLOADS_DIR',
    'GG_EMAIL_PROVIDER',
    'GG_LOG_LEVEL',
    'SENDGRID_API_KEY',
    'SMTP_HOST',
    'SMTP_PORT',
    'SMTP_USER',
    'SMTP_PASS',
    'RESEND_FROM',
    'RESEND_FROM_ROADIELABS',
}


class Config:
    """Pipeline configuration manager."""

    _instance = None
    _config = None
    _lock = threading.Lock()  # Thread-safe singleton

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self._load_config()

    def _load_config(self):
        """Load configuration from config.yaml."""
        # Find config file (check multiple locations)
        possible_paths = [
            Path(__file__).parent.parent.parent / 'config.yaml',  # athletes/scripts -> athlete-profiles/
            Path(__file__).parent.parent.parent.parent / 'config.yaml',  # One more level up
            Path.cwd() / 'config.yaml',
            Path.home() / '.gravelgod' / 'config.yaml',
        ]

        config_path = None
        for path in possible_paths:
            if path.exists():
                config_path = path
                break

        if config_path is None:
            # Use defaults if no config found
            self._config = self._get_defaults()
            return

        with open(config_path, 'r') as f:
            raw_config = yaml.safe_load(f)

        # Process environment variable substitutions
        self._config = self._process_env_vars(raw_config)

    def _process_env_vars(self, obj: Any) -> Any:
        """
        Recursively process environment variable substitutions.

        SECURITY: Only allowlisted environment variables can be substituted.
        """
        if isinstance(obj, str):
            # Pattern: ${VAR_NAME:-default_value} or ${VAR_NAME}
            pattern = r'\$\{([^}:]+)(?::-([^}]*))?\}'

            def replace(match):
                var_name = match.group(1)
                default = match.group(2) or ''

                # SECURITY: Only allow specific environment variables
                if var_name not in ALLOWED_ENV_VARS:
                    # Return default or empty string for non-allowlisted vars
                    return default

                return os.environ.get(var_name, default)

            return re.sub(pattern, replace, obj)

        elif isinstance(obj, dict):
            return {k: self._process_env_vars(v) for k, v in obj.items()}

        elif isinstance(obj, list):
            return [self._process_env_vars(item) for item in obj]

        return obj

    def _get_defaults(self) -> Dict:
        """Return default configuration."""
        return {
            'paths': {
                'guides_repo': '../guides/gravel-god-guides',
                'brand_repo': '../gravel-god-brand',
                'delivery_dir': './delivery',
                'downloads_dir': str(Path.home() / 'Downloads'),
                'templates': 'templates',
                'generators': 'generators',
                'race_data': 'race_data',
            },
            'pdf': {
                'engines': ['chrome', 'weasyprint', 'wkhtmltopdf'],
                'chrome_paths': {
                    'darwin': '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                    'linux': '/usr/bin/google-chrome',
                    'win32': 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
                },
                'timeout': 60,
            },
            'validation': {
                'ftp_min': 50,
                'ftp_max': 500,
                'weight_min': 40,
                'weight_max': 150,
                'plan_weeks_min': 4,
                'plan_weeks_max': 52,
            },
            'workouts': {
                'progression': {'enabled': True},
                'strength': {'enabled': True, 'sessions_per_week': 2},
            },
        }

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.

        Example: config.get('pdf.timeout', 60)
        """
        keys = key_path.split('.')
        value = self._config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def get_path(self, key: str) -> Optional[Path]:
        """
        Get a path configuration, resolving relative paths.

        SECURITY: Validates that paths stay within allowed boundaries.
        """
        raw_path = self.get(f'paths.{key}', '')

        if not raw_path:
            return None

        # Expand ~ to home directory
        expanded = os.path.expanduser(raw_path)

        # Make relative paths relative to athlete-profiles root
        path = Path(expanded)
        base = Path(__file__).parent.parent.parent  # athlete-profiles/

        if not path.is_absolute():
            path = base / path

        resolved = path.resolve()

        # SECURITY: Validate path is within allowed boundaries
        # Allow paths within:
        # 1. The project root (athlete-profiles and siblings)
        # 2. User's home directory
        # 3. Standard system paths for binaries
        project_root = base.parent.resolve()  # GravelGod/
        home_dir = Path.home().resolve()
        allowed_roots = [
            project_root,
            home_dir,
            Path('/usr/bin'),
            Path('/usr/local/bin'),
            Path('/Applications'),
        ]

        is_allowed = any(
            self._is_path_under(resolved, allowed_root)
            for allowed_root in allowed_roots
        )

        if not is_allowed:
            # Log warning but don't expose the attempted path
            import sys
            print(f"WARNING: Path for '{key}' is outside allowed directories", file=sys.stderr)
            return None

        return resolved

    def _is_path_under(self, path: Path, root: Path) -> bool:
        """Check if path is under root directory."""
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False

    def get_brand(self, brand: str = None) -> Dict:
        """Return one brand's production configuration from brands.yaml."""
        return get_brand_config(normalize_brand(brand))

    def get_brand_for_profile(self, profile: dict = None) -> Dict:
        return self.get_brand(brand_from_profile(profile or {}))

    def get_brand_path(self, key: str, brand: str = None) -> Optional[Path]:
        """Resolve a brand-owned path with the same boundary checks as paths.*."""
        brand_paths = self.get_brand(brand).get('paths', {})
        raw_path = brand_paths.get(key, '')
        env_name = brand_paths.get(f'{key}_env', '')
        if env_name in ALLOWED_ENV_VARS and os.environ.get(env_name):
            raw_path = os.environ[env_name]
        if not raw_path:
            return None
        expanded = os.path.expanduser(str(raw_path))
        path = Path(expanded)
        base = Path(__file__).parent.parent.parent
        if not path.is_absolute():
            path = base / path
        resolved = path.resolve()
        allowed_roots = [base.parent.resolve(), Path.home().resolve()]
        if not any(self._is_path_under(resolved, root) for root in allowed_roots):
            print(f"WARNING: Brand path for '{key}' is outside allowed directories",
                  file=__import__('sys').stderr)
            return None
        return resolved

    def get_guides_dir(self, brand: str = None) -> Path:
        """Get the brand-specific guides repository directory."""
        if brand:
            return self.get_brand_path('guides_repo', brand)
        return self.get_path('guides_repo')

    def get_chrome_path(self) -> Optional[str]:
        """Get the Chrome executable path for the current platform."""
        import sys
        platform = sys.platform

        chrome_paths = self.get('pdf.chrome_paths', {})
        path = chrome_paths.get(platform)

        if path and Path(path).exists():
            return path

        # Try common locations
        common_paths = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
            '/usr/bin/chromium',
            '/usr/bin/chromium-browser',
        ]

        for p in common_paths:
            if Path(p).exists():
                return p

        return None

    @property
    def all(self) -> Dict:
        """Return the full configuration dictionary."""
        return self._config


# Global config instance
config = Config()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config
