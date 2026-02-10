#!/usr/bin/env python3
"""
Structured logging for Gravel God pipeline.

Replaces print() statements with proper logging that:
- Has timestamps
- Has log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Can output to file or stdout
- Is machine-parseable
- Works in CI/CD
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class PipelineLogger:
    """Structured logger for the training plan pipeline."""

    _instance = None
    _logger = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._logger is None:
            self._setup_logger()

    def _setup_logger(self):
        """Configure the logger."""
        self._logger = logging.getLogger('gravelgod')
        self._logger.setLevel(logging.DEBUG)

        # Prevent duplicate handlers
        if self._logger.handlers:
            return

        # Console handler (INFO and above)
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        console_fmt = logging.Formatter(
            '%(message)s'  # Clean output for console
        )
        console.setFormatter(console_fmt)
        self._logger.addHandler(console)

    def set_level(self, level: str):
        """Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)."""
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL,
        }
        self._logger.setLevel(level_map.get(level.upper(), logging.INFO))

    def add_file_handler(self, log_path: Path):
        """Add file handler for persistent logs."""
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_fmt)
        self._logger.addHandler(file_handler)

    # === Logging methods ===

    def debug(self, msg: str, **kwargs):
        """Debug level message."""
        self._logger.debug(self._format(msg, **kwargs))

    def info(self, msg: str, **kwargs):
        """Info level message."""
        self._logger.info(self._format(msg, **kwargs))

    def warning(self, msg: str, **kwargs):
        """Warning level message."""
        self._logger.warning(f"⚠️  {self._format(msg, **kwargs)}")

    def error(self, msg: str, **kwargs):
        """Error level message."""
        self._logger.error(f"❌ {self._format(msg, **kwargs)}")

    def critical(self, msg: str, **kwargs):
        """Critical level message."""
        self._logger.critical(f"🚨 {self._format(msg, **kwargs)}")

    def success(self, msg: str, **kwargs):
        """Success message (INFO level with checkmark)."""
        self._logger.info(f"✓ {self._format(msg, **kwargs)}")

    def step(self, step_num: int, msg: str, **kwargs):
        """Step message for multi-step processes."""
        self._logger.info(f"\n{step_num}. {self._format(msg, **kwargs)}")

    def header(self, title: str):
        """Section header."""
        line = "=" * 60
        self._logger.info(f"\n{line}\n{title}\n{line}")

    def subheader(self, title: str):
        """Subsection header."""
        self._logger.info(f"\n--- {title} ---")

    def detail(self, msg: str, indent: int = 1, **kwargs):
        """Indented detail message."""
        prefix = "   " * indent
        self._logger.info(f"{prefix}{self._format(msg, **kwargs)}")

    def _format(self, msg: str, **kwargs) -> str:
        """Format message with optional key-value pairs."""
        if kwargs:
            pairs = ' | '.join(f"{k}={v}" for k, v in kwargs.items())
            return f"{msg} [{pairs}]"
        return msg


# Global logger instance
_logger = None


def get_logger() -> PipelineLogger:
    """Get the global logger instance."""
    global _logger
    if _logger is None:
        _logger = PipelineLogger()
    return _logger


# Convenience functions
def debug(msg: str, **kwargs):
    get_logger().debug(msg, **kwargs)


def info(msg: str, **kwargs):
    get_logger().info(msg, **kwargs)


def warning(msg: str, **kwargs):
    get_logger().warning(msg, **kwargs)


def error(msg: str, **kwargs):
    get_logger().error(msg, **kwargs)


def critical(msg: str, **kwargs):
    get_logger().critical(msg, **kwargs)


def success(msg: str, **kwargs):
    get_logger().success(msg, **kwargs)


def step(step_num: int, msg: str, **kwargs):
    get_logger().step(step_num, msg, **kwargs)


def header(title: str):
    get_logger().header(title)


def subheader(title: str):
    get_logger().subheader(title)


def detail(msg: str, indent: int = 1, **kwargs):
    get_logger().detail(msg, indent, **kwargs)
