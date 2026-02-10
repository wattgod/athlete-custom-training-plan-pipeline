#!/usr/bin/env python3
"""
Configuration loader for Gravel God pipeline.

Loads settings from config.yaml with environment variable overrides.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """Pipeline configuration manager."""

    _instance = None
    _config = None

    def __new__(cls):
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
        """Recursively process environment variable substitutions."""
        if isinstance(obj, str):
            # Pattern: ${VAR_NAME:-default_value} or ${VAR_NAME}
            pattern = r'\$\{([^}:]+)(?::-([^}]*))?\}'

            def replace(match):
                var_name = match.group(1)
                default = match.group(2) or ''
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

    def get_path(self, key: str) -> Path:
        """Get a path configuration, resolving relative paths."""
        raw_path = self.get(f'paths.{key}', '')

        if not raw_path:
            return None

        # Expand ~ to home directory
        expanded = os.path.expanduser(raw_path)

        # Make relative paths relative to athlete-profiles root
        path = Path(expanded)
        if not path.is_absolute():
            base = Path(__file__).parent.parent.parent  # athlete-profiles/
            path = base / path

        return path.resolve()

    def get_guides_dir(self) -> Path:
        """Get the gravel-god-guides directory."""
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
