"""
Middleware Components

Custom middleware for FastAPI backend including error handling,
logging, CORS, rate limiting, and request validation.
"""

import time
import uuid
import logging
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response, HTTPException
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse
import asyncio
from collections import defaultdict, deque

from backend.config import config
from backend.schemas import ErrorResponse, create_error_response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request logging and monitoring."""
    
    def __init__(self, app, logger: Optional[logging.Logger] = None):
        super().__init__(app)
        self.logger = logger or logging.getLogger(__name__)
        self.request_count = 0
        self.start_time = time.time()
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Log request and response information."""
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Record request start time
        start_time = time.time()
        
        # Log request
        self.request_count += 1
        
        if config.enable_request_logging:
            self.logger.info(
                "Request started",
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                client_ip=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "unknown"),
                request_number=self.request_count
            )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Log response
            if config.enable_request_logging:
                self.logger.info(
                    "Request completed",
                    request_id=request_id,
                    status_code=response.status_code,
                    processing_time_ms=processing_time * 1000,
                    response_size=len(response.body) if hasattr(response, 'body') else 0
                )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Processing-Time"] = f"{processing_time:.3f}"
            
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            self.logger.error(
                "Request failed",
                request_id=request_id,
                error=str(e),
                processing_time_ms=processing_time * 1000
            )
            
            # Return error response
            error_response = create_error_response(
                error_type="INTERNAL_SERVER_ERROR",
                message="Internal server error occurred",
                details={"request_id": request_id}
            )
            
            return JSONResponse(
                status_code=500,
                content=error_response.dict()
            )


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for centralized error handling."""
    
    def __init__(self, app, logger: Optional[logging.Logger] = None):
        super().__init__(app)
        self.logger = logger or logging.getLogger(__name__)
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Handle exceptions and return standardized error responses."""
        
        try:
            response = await call_next(request)
            return response
            
        except HTTPException as e:
            # Handle HTTP exceptions
            self.logger.warning(
                "HTTP exception",
                status_code=e.status_code,
                detail=e.detail,
                request_id=getattr(request.state, 'request_id', 'unknown')
            )
            
            error_response = create_error_response(
                error_type="HTTP_ERROR",
                message=e.detail,
                details={"status_code": e.status_code}
            )
            
            return JSONResponse(
                status_code=e.status_code,
                content=error_response.dict()
            )
            
        except ValueError as e:
            # Handle validation errors
            self.logger.warning(
                "Validation error",
                error=str(e),
                request_id=getattr(request.state, 'request_id', 'unknown')
            )
            
            error_response = create_error_response(
                error_type="VALIDATION_ERROR",
                message=str(e),
                details={"error_type": "value_error"}
            )
            
            return JSONResponse(
                status_code=422,
                content=error_response.dict()
            )
            
        except asyncio.TimeoutError as e:
            # Handle timeout errors
            self.logger.error(
                "Request timeout",
                error=str(e),
                request_id=getattr(request.state, 'request_id', 'unknown')
            )
            
            error_response = create_error_response(
                error_type="TIMEOUT_ERROR",
                message="Request timed out",
                details={"timeout_seconds": config.request_timeout}
            )
            
            return JSONResponse(
                status_code=408,
                content=error_response.dict()
            )
            
        except Exception as e:
            # Handle unexpected errors
            self.logger.error(
                "Unexpected error",
                error=str(e),
                error_type=type(e).__name__,
                request_id=getattr(request.state, 'request_id', 'unknown')
            )
            
            error_response = create_error_response(
                error_type="INTERNAL_SERVER_ERROR",
                message="An unexpected error occurred",
                details={"error_type": type(e).__name__}
            )
            
            return JSONResponse(
                status_code=500,
                content=error_response.dict()
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting."""
    
    def __init__(self, app, logger: Optional[logging.Logger] = None):
        super().__init__(app)
        self.logger = logger or logging.getLogger(__name__)
        self.requests = defaultdict(lambda: deque())
        self.window_size = config.rate_limit_window
        self.max_requests = config.rate_limit_requests
    
    def is_rate_limited(self, client_ip: str) -> bool:
        """Check if client is rate limited."""
        now = time.time()
        client_requests = self.requests[client_ip]
        
        # Remove old requests outside the window
        while client_requests and client_requests[0] < now - self.window_size:
            client_requests.popleft()
        
        # Check if client exceeded the limit
        if len(client_requests) >= self.max_requests:
            return True
        
        # Add current request
        client_requests.append(now)
        return False
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Apply rate limiting to requests."""
        
        if not config.enable_rate_limiting:
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"
        
        # Check rate limit
        if self.is_rate_limited(client_ip):
            self.logger.warning(
                "Rate limit exceeded",
                client_ip=client_ip,
                request_id=getattr(request.state, 'request_id', 'unknown')
            )
            
            error_response = create_error_response(
                error_type="RATE_LIMIT_EXCEEDED",
                message="Rate limit exceeded",
                details={
                    "max_requests": self.max_requests,
                    "window_seconds": self.window_size,
                    "retry_after": self.window_size
                }
            )
            
            return JSONResponse(
                status_code=429,
                content=error_response.dict(),
                headers={"Retry-After": str(self.window_size)}
            )
        
        return await call_next(request)


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware for security headers and validation."""
    
    def __init__(self, app, logger: Optional[logging.Logger] = None):
        super().__init__(app)
        self.logger = logger or logging.getLogger(__name__)
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Add security headers and validate requests."""
        
        # Process request
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        # Add API version header
        response.headers["X-API-Version"] = config.api_version
        
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting API metrics."""
    
    def __init__(self, app, logger: Optional[logging.Logger] = None):
        super().__init__(app)
        self.logger = logger or logging.getLogger(__name__)
        
        # Metrics storage
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.blocked_requests = 0
        self.response_times = deque(maxlen=1000)  # Keep last 1000 response times
        self.start_time = time.time()
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Collect metrics for requests."""
        
        start_time = time.time()
        self.total_requests += 1
        
        try:
            response = await call_next(request)
            
            # Record response time
            response_time = time.time() - start_time
            self.response_times.append(response_time)
            
            # Count successful requests
            if 200 <= response.status_code < 400:
                self.successful_requests += 1
            elif response.status_code >= 400:
                self.failed_requests += 1
            
            # Add metrics to response headers (for debugging)
            if config.enable_metrics:
                response.headers["X-Metrics-Total-Requests"] = str(self.total_requests)
                response.headers["X-Metrics-Response-Time"] = f"{response_time:.3f}"
            
            return response
            
        except Exception as e:
            self.failed_requests += 1
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        uptime = time.time() - self.start_time
        avg_response_time = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        requests_per_minute = (self.total_requests / uptime) * 60 if uptime > 0 else 0
        uptime_percentage = (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0
        
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "blocked_requests": self.blocked_requests,
            "average_response_time_ms": avg_response_time * 1000,
            "requests_per_minute": requests_per_minute,
            "uptime_percentage": uptime_percentage,
            "uptime_seconds": uptime
        }


def setup_cors_middleware(app):
    """Setup CORS middleware."""
    app.add_middleware(
        CORSMiddleware,
        **config.get_cors_config()
    )


def setup_middleware(app, logger: Optional[logging.Logger] = None):
    """Setup all middleware components."""
    
    # Setup CORS first
    setup_cors_middleware(app)
    
    # Add custom middleware in order
    app.add_middleware(SecurityMiddleware, logger=logger)
    app.add_middleware(MetricsMiddleware, logger=logger)
    app.add_middleware(RateLimitMiddleware, logger=logger)
    app.add_middleware(ErrorHandlingMiddleware, logger=logger)
    app.add_middleware(RequestLoggingMiddleware, logger=logger)
