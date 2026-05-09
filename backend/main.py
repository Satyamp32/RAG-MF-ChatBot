"""
FastAPI Backend Main Application

Main FastAPI application for Mutual Fund RAG ChatBot with modular architecture,
retrieval + generation integration, and comprehensive API endpoints.
"""

import time
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from backend.config import config
from backend.schemas import (
    ChatRequest, ChatResponse, HealthCheck, APIInfo, ErrorResponse,
    Metrics, create_error_response
)
from backend.services import ChatService
from backend.middleware import setup_middleware
from backend.logger import get_logger

logger = get_logger(__name__)

# Global service instance
chat_service = ChatService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting FastAPI application")
    
    # Initialize services
    try:
        initialized = await chat_service.initialize()
        if not initialized:
            logger.error("Failed to initialize chat service")
            raise RuntimeError("Service initialization failed")
        
        logger.info("FastAPI application started successfully")
        yield
        
    except Exception as e:
        logger.error("Application startup failed", error=str(e))
        raise
    
    # Shutdown
    logger.info("Shutting down FastAPI application")
    # Cleanup resources if needed
    logger.info("FastAPI application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=config.api_title,
    description=config.api_description,
    version=config.api_version,
    debug=config.api_debug,
    lifespan=lifespan
)


# Setup middleware
setup_middleware(app, logger)


# Add trusted host middleware for security
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "0.0.0.0"] + 
                   [origin.split("//")[1].split(":")[0] for origin in config.cors_origins if "//" in origin]
)


# Dependencies
async def get_chat_service() -> ChatService:
    """Get chat service instance."""
    return chat_service


# Health and Metadata Endpoints
@app.get("/health", response_model=HealthCheck, tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns the health status of the application and its components.
    """
    try:
        # Get service health
        service_health = await chat_service.health_check()
        
        # Get uptime
        uptime = time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0
        
        health_response = HealthCheck(
            status="healthy" if service_health["status"] == "healthy" else "unhealthy",
            version=config.api_version,
            uptime_seconds=uptime,
            components=service_health["components"]
        )
        
        return health_response
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail="Service unavailable"
        )


@app.get("/meta", response_model=APIInfo, tags=["Metadata"])
async def get_api_info():
    """
    API metadata endpoint.
    
    Returns information about the API including available endpoints and features.
    """
    try:
        endpoints = [
            "/health",
            "/meta",
            "/chat",
            "/metrics"
        ]
        
        features = [
            "Hybrid Retrieval (Dense + Sparse)",
            "Cross-Encoder Reranking",
            "Groq LLM Integration",
            "Guardrails and Safety",
            "Source Attribution",
            "Confidence Scoring",
            "Rate Limiting",
            "Request Logging"
        ]
        
        return APIInfo(
            title=config.api_title,
            description=config.api_description,
            version=config.api_version,
            docs_url="/docs",
            health_url="/health",
            endpoints=endpoints,
            features=features
        )
        
    except Exception as e:
        logger.error("API info retrieval failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve API information"
        )


@app.get("/metrics", response_model=Metrics, tags=["Monitoring"])
async def get_metrics():
    """
    Metrics endpoint.
    
    Returns application metrics including request counts, response times, and uptime.
    """
    try:
        # Get metrics from middleware (if available)
        # This would need to be implemented to collect actual metrics
        metrics = Metrics(
            total_requests=0,  # Would be populated from actual metrics
            successful_requests=0,
            failed_requests=0,
            blocked_requests=0,
            average_response_time_ms=0.0,
            requests_per_minute=0.0,
            uptime_percentage=100.0
        )
        
        return metrics
        
    except Exception as e:
        logger.error("Metrics retrieval failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve metrics"
        )


# Chat Endpoint
@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Chat endpoint for processing user queries.
    
    Processes a user query about mutual funds and returns a factual answer
    with source attribution and confidence scoring.
    """
    try:
        logger.info(
            "Chat request received",
            query=request.query[:100],
            use_groq=request.use_groq,
            top_k=request.top_k
        )
        
        # Process chat request
        response = await chat_service.process_chat_request(request)
        
        # Log response in background (non-blocking)
        background_tasks.add_task(
            log_chat_response,
            request.query,
            response.status.value,
            response.confidence
        )
        
        return response
        
    except ValueError as e:
        logger.warning("Chat request validation failed", error=str(e))
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )
    
    except RuntimeError as e:
        logger.error("Chat service not available", error=str(e))
        raise HTTPException(
            status_code=503,
            detail="Chat service not available"
        )
    
    except Exception as e:
        logger.error("Chat request processing failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


# Utility Functions
async def log_chat_response(query: str, status: str, confidence: Optional[float]):
    """Log chat response for analytics."""
    try:
        logger.info(
            "Chat response logged",
            query=query[:100],
            status=status,
            confidence=confidence
        )
    except Exception as e:
        logger.error("Failed to log chat response", error=str(e))


# Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.warning(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        request_id=getattr(request.state, 'request_id', 'unknown')
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            error_type="HTTP_ERROR",
            message=exc.detail,
            details={"status_code": exc.status_code}
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(
        "Unhandled exception",
        error=str(exc),
        error_type=type(exc).__name__,
        request_id=getattr(request.state, 'request_id', 'unknown')
    )
    
    return JSONResponse(
        status_code=500,
        content=create_error_response(
            error_type="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred",
            details={"error_type": type(exc).__name__}
        ).dict()
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    app.state.start_time = time.time()
    logger.info(
        "FastAPI application startup complete",
        host=config.api_host,
        port=config.api_port,
        debug=config.api_debug
    )


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("FastAPI application shutdown event triggered")


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": "Mutual Fund RAG ChatBot API",
        "version": config.api_version,
        "docs": "/docs",
        "health": "/health",
        "chat": "/chat"
    }


# Development server startup
if __name__ == "__main__":
    import uvicorn
    
    # Setup logging
    from backend.logger import setup_logging
    setup_logging()
    
    logger.info(
        "Starting development server",
        host=config.api_host,
        port=config.api_port,
        debug=config.api_debug
    )
    
    uvicorn.run(
        "backend.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.api_debug,
        log_level=config.log_level.lower()
    )
