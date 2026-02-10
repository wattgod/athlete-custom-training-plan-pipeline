#!/usr/bin/env python3
"""
Structured logging for Gravel God pipeline.

Supports two modes:
- Human-readable: Pretty output for interactive use
- JSON: Machine-parseable structured logs for CI/CD

Set GG_LOG_FORMAT=json for structured output.
"""

import json
import logging
import os
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class StructuredFormatter(logging.Formatter):
    """JSON formatter for machine-parseable logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
        }

        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_obj['fields'] = record.extra_fields

        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


class HumanFormatter(logging.Formatter):
    """Human-readable formatter for interactive use."""

    # Level prefixes without emojis for parseability
    LEVEL_PREFIXES = {
        'DEBUG': '[DEBUG]',
        'INFO': '',
        'WARNING': '[WARN]',
        'ERROR': '[ERROR]',
        'CRITICAL': '[CRITICAL]',
    }

    def format(self, record: logging.LogRecord) -> str:
        prefix = self.LEVEL_PREFIXES.get(record.levelname, '')
        msg = record.getMessage()

        if prefix:
            return f"{prefix} {msg}"
        return msg


class PipelineLogger:
    """Structured logger for the training plan pipeline."""

    _instance = None
    _logger = None
    _lock = threading.Lock()  # Thread-safe singleton
    _json_mode = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
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

        # Check for JSON mode via environment variable
        self._json_mode = os.environ.get('GG_LOG_FORMAT', '').lower() == 'json'

        # Console handler
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)

        if self._json_mode:
            console.setFormatter(StructuredFormatter())
        else:
            console.setFormatter(HumanFormatter())

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

    def set_json_mode(self, enabled: bool):
        """Enable or disable JSON output mode."""
        self._json_mode = enabled
        # Update formatter on existing handlers
        for handler in self._logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                if enabled:
                    handler.setFormatter(StructuredFormatter())
                else:
                    handler.setFormatter(HumanFormatter())

    def add_file_handler(self, log_path: Path, json_format: bool = True):
        """Add file handler for persistent logs."""
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)

        if json_format:
            file_handler.setFormatter(StructuredFormatter())
        else:
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))

        self._logger.addHandler(file_handler)

    # === Core logging methods ===

    def _log(self, level: int, msg: str, **kwargs):
        """Internal log method with extra fields support."""
        record = self._logger.makeRecord(
            self._logger.name,
            level,
            "(unknown file)",
            0,
            msg,
            (),
            None,
        )
        if kwargs:
            record.extra_fields = kwargs
        self._logger.handle(record)

    def debug(self, msg: str, **kwargs):
        """Debug level message."""
        self._log(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs):
        """Info level message."""
        if kwargs and not self._json_mode:
            # Append key-value pairs for human-readable mode
            pairs = ' | '.join(f"{k}={v}" for k, v in kwargs.items())
            msg = f"{msg} [{pairs}]"
        self._log(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        """Warning level message."""
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs):
        """Error level message."""
        self._log(logging.ERROR, msg, **kwargs)

    def critical(self, msg: str, **kwargs):
        """Critical level message."""
        self._log(logging.CRITICAL, msg, **kwargs)

    # === Convenience methods for human-readable output ===
    # These produce structured output in JSON mode

    def success(self, msg: str, **kwargs):
        """Success message (INFO level)."""
        if self._json_mode:
            kwargs['status'] = 'success'
            self._log(logging.INFO, msg, **kwargs)
        else:
            self._log(logging.INFO, f"[OK] {msg}", **kwargs)

    def step(self, step_num: int, msg: str, **kwargs):
        """Step message for multi-step processes."""
        if self._json_mode:
            kwargs['step'] = step_num
            self._log(logging.INFO, msg, **kwargs)
        else:
            self._log(logging.INFO, f"\n{step_num}. {msg}")

    def header(self, title: str):
        """Section header."""
        if self._json_mode:
            self._log(logging.INFO, title, section='header')
        else:
            line = "=" * 60
            self._log(logging.INFO, f"\n{line}\n{title}\n{line}")

    def subheader(self, title: str):
        """Subsection header."""
        if self._json_mode:
            self._log(logging.INFO, title, section='subheader')
        else:
            self._log(logging.INFO, f"\n--- {title} ---")

    def detail(self, msg: str, indent: int = 1, **kwargs):
        """Indented detail message."""
        if self._json_mode:
            kwargs['indent'] = indent
            self._log(logging.INFO, msg, **kwargs)
        else:
            prefix = "   " * indent
            self._log(logging.INFO, f"{prefix}{msg}")


# Thread-safe global logger instance
_logger = None
_logger_lock = threading.Lock()


def get_logger() -> PipelineLogger:
    """Get the global logger instance."""
    global _logger
    if _logger is None:
        with _logger_lock:
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
