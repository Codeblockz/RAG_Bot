"""
Security utilities for authentication, authorization, and input validation.

This module provides security features including API key authentication,
rate limiting, input sanitization, and request validation.
"""

import hashlib
import hmac
import secrets
import time
from typing import List, Optional

from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.api_key import APIKeyHeader

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)


# API Key authentication
api_key_header = APIKeyHeader(
    name=settings.security.api_key_header,
    auto_error=False
)


class APIKeyAuth:
    """API Key authentication handler."""
    
    def __init__(self, api_keys: Optional[List[str]] = None):
        """Initialize with allowed API keys."""
        self.api_keys = set(api_keys or settings.security.allowed_api_keys)
        self.logger = get_logger(self.__class__.__name__)
    
    async def __call__(self, api_key: Optional[str] = None) -> str:
        """Validate API key."""
        if not api_key:
            self.logger.warning("Missing API key in request")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required"
            )
        
        if not self.api_keys or api_key not in self.api_keys:
            self.logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        self.logger.debug(f"Valid API key authenticated: {api_key[:8]}...")
        return api_key


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, requests_per_minute: int = 100):
        """Initialize rate limiter with requests per minute limit."""
        self.requests_per_minute = requests_per_minute
        self.requests = {}
        self.logger = get_logger(self.__class__.__name__)
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if client is allowed to make request."""
        now = time.time()
        minute = int(now // 60)
        
        # Clean old entries
        old_minutes = [m for m in self.requests.keys() if m < minute - 1]
        for old_minute in old_minutes:
            del self.requests[old_minute]
        
        # Check current minute requests
        key = (client_id, minute)
        current_requests = self.requests.get(key, 0)
        
        if current_requests >= self.requests_per_minute:
            self.logger.warning(
                f"Rate limit exceeded for client {client_id}: "
                f"{current_requests} requests this minute"
            )
            return False
        
        # Increment counter
        self.requests[key] = current_requests + 1
        return True
    
    def get_client_id(self, request: Request) -> str:
        """Extract client ID from request."""
        # Use IP address as client ID
        client_ip = request.client.host if request.client else "unknown"
        
        # Check for forwarded IP headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            client_ip = real_ip
        
        return client_ip


# Global rate limiter instance
rate_limiter = RateLimiter(settings.api.rate_limit_requests)


async def check_rate_limit(request: Request) -> None:
    """Check rate limit for request."""
    client_id = rate_limiter.get_client_id(request)
    
    if not rate_limiter.is_allowed(client_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": "60"}
        )


def generate_secret_key(length: int = 32) -> str:
    """Generate a secure random secret key."""
    return secrets.token_urlsafe(length)


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hash password with salt."""
    if salt is None:
        salt = secrets.token_hex(16)
    
    password_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000  # iterations
    )
    
    return password_hash.hex(), salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Verify password against hash."""
    computed_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(computed_hash, password_hash)


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """Sanitize user input."""
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    
    # Truncate if too long
    if len(text) > max_length:
        logger.warning(f"Input truncated from {len(text)} to {max_length} characters")
        text = text[:max_length]
    
    # Remove or escape potentially dangerous characters
    # For now, just strip and normalize whitespace
    text = text.strip()
    text = ' '.join(text.split())  # Normalize whitespace
    
    return text


def validate_file_upload(
    filename: str,
    file_size: int,
    allowed_extensions: Optional[List[str]] = None
) -> None:
    """Validate file upload parameters."""
    if allowed_extensions is None:
        allowed_extensions = ['.txt', '.pdf', '.docx', '.doc', '.md']
    
    # Check file size
    if file_size > settings.max_document_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.max_document_size} bytes"
        )
    
    # Check file extension
    if filename:
        extension = '.' + filename.lower().split('.')[-1] if '.' in filename else ''
        if extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed types: {allowed_extensions}"
            )
    
    # Basic filename validation
    if not filename or len(filename) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename"
        )
    
    # Check for dangerous characters in filename
    dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
    if any(char in filename for char in dangerous_chars):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename contains invalid characters"
        )


def create_request_id() -> str:
    """Create a unique request ID for tracing."""
    return secrets.token_urlsafe(16)


def get_request_id(request: Request) -> str:
    """Get or create request ID from request."""
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = create_request_id()
    return request_id


class SecurityHeaders:
    """Security headers middleware."""
    
    @staticmethod
    def get_security_headers() -> dict:
        """Get recommended security headers."""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:;"
            ),
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": (
                "camera=(), microphone=(), geolocation=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=()"
            )
        }


# Create API key authentication instance
api_key_auth = APIKeyAuth()
