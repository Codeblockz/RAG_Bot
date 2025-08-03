"""
Core module for RAG Chatbot.

This module provides core functionality including configuration management,
logging, security, and shared utilities.
"""

from .config import settings
from .logging import setup_logging, get_logger, app_logger
from .security import api_key_auth, check_rate_limit

__all__ = [
    "settings",
    "setup_logging",
    "get_logger", 
    "app_logger",
    "api_key_auth",
    "check_rate_limit",
]
