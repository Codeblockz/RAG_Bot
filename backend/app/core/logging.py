"""
Structured logging configuration with JSON output support.

This module provides centralized logging setup with context management,
structured output, and integration with cloud logging services.
"""

import json
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .config import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from the record
        extra_fields = getattr(record, 'extra_fields', {})
        if extra_fields:
            log_entry.update(extra_fields)
        
        # Add request context if available
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        if hasattr(record, 'session_id'):
            log_entry["session_id"] = record.session_id
        
        return json.dumps(log_entry, default=str)


class ContextFilter(logging.Filter):
    """Filter to add contextual information to log records."""
    
    def __init__(self, context: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.context = context or {}
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context information to the log record."""
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


def setup_logging() -> None:
    """Configure application logging based on settings."""
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.logging.level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    if settings.logging.format.lower() == "json":
        console_formatter = JSONFormatter()
    else:
        console_formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (if configured)
    if settings.logging.file:
        log_file = Path(settings.logging.file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_file),
            maxBytes=settings.logging.max_size,
            backupCount=settings.logging.backup_count,
            encoding="utf-8"
        )
        
        if settings.logging.format.lower() == "json":
            file_formatter = JSONFormatter()
        else:
            file_formatter = logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Configure specific loggers
    configure_library_loggers()


def configure_library_loggers() -> None:
    """Configure logging for third-party libraries."""
    # Reduce noise from libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("pinecone").setLevel(logging.WARNING)
    
    # Set appropriate levels for SQL logging
    if settings.database.echo:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    else:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to other classes."""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class."""
        return get_logger(self.__class__.__name__)


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    extra_fields: Optional[Dict[str, Any]] = None,
    **kwargs
) -> None:
    """Log a message with additional context fields."""
    record_kwargs = kwargs.copy()
    if extra_fields:
        record_kwargs['extra_fields'] = extra_fields
    
    logger.log(level, message, extra=record_kwargs)


def log_api_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    """Log API request with structured data."""
    extra_fields = {
        "request_method": method,
        "request_path": path,
        "response_status": status_code,
        "duration_ms": duration_ms,
    }
    
    log_kwargs = {}
    if request_id:
        log_kwargs['request_id'] = request_id
    if user_id:
        log_kwargs['user_id'] = user_id
    
    log_with_context(
        logger,
        logging.INFO,
        f"{method} {path} - {status_code} ({duration_ms:.2f}ms)",
        extra_fields=extra_fields,
        **log_kwargs
    )


def log_llm_request(
    logger: logging.Logger,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    duration_ms: float,
    cost: Optional[float] = None,
    request_id: Optional[str] = None,
) -> None:
    """Log LLM request with cost and token tracking."""
    extra_fields = {
        "llm_provider": provider,
        "llm_model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "duration_ms": duration_ms,
    }
    
    if cost is not None:
        extra_fields["cost_usd"] = cost
    
    log_kwargs = {}
    if request_id:
        log_kwargs['request_id'] = request_id
    
    message = (
        f"LLM Request - {provider}/{model} "
        f"({prompt_tokens}+{completion_tokens} tokens, {duration_ms:.2f}ms)"
    )
    if cost is not None:
        message += f" ${cost:.4f}"
    
    log_with_context(
        logger,
        logging.INFO,
        message,
        extra_fields=extra_fields,
        **log_kwargs
    )


def log_vector_search(
    logger: logging.Logger,
    provider: str,
    query: str,
    results_count: int,
    duration_ms: float,
    request_id: Optional[str] = None,
) -> None:
    """Log vector search operation."""
    extra_fields = {
        "vector_provider": provider,
        "query_length": len(query),
        "results_count": results_count,
        "duration_ms": duration_ms,
    }
    
    log_kwargs = {}
    if request_id:
        log_kwargs['request_id'] = request_id
    
    log_with_context(
        logger,
        logging.INFO,
        f"Vector Search - {provider} ({results_count} results, {duration_ms:.2f}ms)",
        extra_fields=extra_fields,
        **log_kwargs
    )


def log_document_processing(
    logger: logging.Logger,
    filename: str,
    file_size: int,
    chunks_created: int,
    duration_ms: float,
    request_id: Optional[str] = None,
) -> None:
    """Log document processing operation."""
    extra_fields = {
        "filename": filename,
        "file_size_bytes": file_size,
        "chunks_created": chunks_created,
        "duration_ms": duration_ms,
    }
    
    log_kwargs = {}
    if request_id:
        log_kwargs['request_id'] = request_id
    
    log_with_context(
        logger,
        logging.INFO,
        f"Document Processing - {filename} ({chunks_created} chunks, {duration_ms:.2f}ms)",
        extra_fields=extra_fields,
        **log_kwargs
    )


# Application logger
app_logger = get_logger("rag_chatbot")
