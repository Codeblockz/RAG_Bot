"""
FastAPI application entry point.

This module sets up the FastAPI application with middleware, error handling,
and route registration.
"""

import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .core import settings, setup_logging, get_logger, check_rate_limit
from .core.security import SecurityHeaders, get_request_id
from .services.factory import ServiceFactory


# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    
    # Validate service connections
    try:
        connections = await ServiceFactory.validate_all_connections()
        for service, status in connections.items():
            if status:
                logger.info(f"✓ {service} connection validated")
            else:
                logger.warning(f"✗ {service} connection failed")
    except Exception as e:
        logger.error(f"Service validation error: {e}")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")
    ServiceFactory.clear_instances()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A production-ready RAG chatbot with modular architecture",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests."""
    
    async def dispatch(self, request: Request, call_next):
        """Process request and log details."""
        start_time = time.time()
        request_id = get_request_id(request)
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        # Process request
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            
            # Log request
            logger.info(
                f"{request.method} {request.url.path} - "
                f"{response.status_code} ({duration_ms:.2f}ms)",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "client_ip": request.client.host if request.client else "unknown",
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"{request.method} {request.url.path} - ERROR ({duration_ms:.2f}ms): {e}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error": str(e),
                }
            )
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers."""
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)
        
        # Add security headers
        security_headers = SecurityHeaders.get_security_headers()
        for header, value in security_headers.items():
            response.headers[header] = value
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting."""
    
    async def dispatch(self, request: Request, call_next):
        """Check rate limits before processing request."""
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/health", "/ready", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Check rate limit
        try:
            await check_rate_limit(request)
        except HTTPException:
            # Rate limit exceeded
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded. Please try again later."},
                headers={"Retry-After": "60"}
            )
        
        return await call_next(request)


# Add middleware (order matters - last added is executed first)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=settings.api.cors_methods,
    allow_headers=settings.api.cors_headers,
)

# Trusted host middleware for production
if settings.environment == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure with actual hosts in production
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        f"Unhandled exception in {request.method} {request.url.path}: {exc}",
        extra={"request_id": request_id},
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": request_id,
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP exception handler."""
    request_id = getattr(request.state, "request_id", "unknown")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "request_id": request_id,
        }
    )


# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/ready")
async def readiness_check():
    """Readiness check with service validation."""
    try:
        # Quick validation of core services
        connections = await ServiceFactory.validate_all_connections()
        
        all_healthy = all(connections.values())
        status_code = 200 if all_healthy else 503
        
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "ready" if all_healthy else "not ready",
                "services": connections,
                "timestamp": time.time(),
            }
        )
    
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "not ready",
                "error": str(e),
                "timestamp": time.time(),
            }
        )


@app.get("/info")
async def app_info():
    """Application information endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "available_providers": ServiceFactory.get_available_providers(),
    }


# Include API routes
# NOTE: Routes will be added in Phase 2
# from .api.routes import router as api_router
# app.include_router(api_router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api.host,
        port=settings.api.port,
        reload=settings.api.reload,
        workers=1 if settings.api.reload else settings.api.workers,
        log_config=None,  # Use our custom logging
    )
