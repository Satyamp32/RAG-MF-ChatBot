"""
Backend Configuration

Manages FastAPI backend configuration, environment variables,
and settings for the Mutual Fund RAG ChatBot.
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, Field


class BackendConfig(BaseSettings):
    """Backend configuration settings."""
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host address")
    api_port: int = Field(default=8000, description="API port")
    api_debug: bool = Field(default=False, description="Enable debug mode")
    api_title: str = Field(default="Mutual Fund RAG ChatBot API", description="API title")
    api_description: str = Field(
        default="FastAPI backend for Mutual Fund RAG ChatBot with retrieval and generation",
        description="API description"
    )
    api_version: str = Field(default="1.0.0", description="API version")
    
    # CORS Configuration
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="CORS allowed origins"
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow CORS credentials")
    cors_allow_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        description="CORS allowed methods"
    )
    cors_allow_headers: List[str] = Field(
        default=["*"],
        description="CORS allowed headers"
    )
    
    # Security Configuration
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for security"
    )
    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time in minutes"
    )
    
    # Database Configuration
    chroma_persist_directory: str = Field(
        default="./data/vectorstore",
        description="ChromaDB persist directory"
    )
    
    # LLM Configuration
    groq_api_key: Optional[str] = Field(
        default=None,
        description="Groq API key for LLM generation"
    )
    groq_model: str = Field(
        default="llama3-70b-8192",
        description="Groq model name"
    )
    groq_temperature: float = Field(
        default=0.1,
        description="Groq generation temperature"
    )
    groq_max_tokens: int = Field(
        default=500,
        description="Groq max tokens for generation"
    )
    
    # Retrieval Configuration
    dense_weight: float = Field(default=0.4, description="Dense retrieval weight")
    sparse_weight: float = Field(default=0.6, description="Sparse retrieval weight")
    top_k: int = Field(default=10, description="Number of top chunks to retrieve")
    enable_reranking: bool = Field(default=True, description="Enable cross-encoder reranking")
    rerank_top_k: int = Field(default=3, description="Number of top chunks after reranking")
    
    # Generation Configuration
    use_groq: str = Field(default="auto", description="Use Groq (auto, true, false)")
    confidence_threshold: float = Field(default=0.3, description="Confidence threshold for responses")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", description="Log level")
    log_file: Optional[str] = Field(default="./logs/backend.log", description="Log file path")
    enable_request_logging: bool = Field(default=True, description="Enable request logging")
    
    # Cache Configuration
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")
    cache_max_size: int = Field(default=1000, description="Maximum cache size")
    enable_cache: bool = Field(default=True, description="Enable response caching")
    
    # Monitoring Configuration
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_port: int = Field(default=9090, description="Metrics port")
    
    # Rate Limiting Configuration
    enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests: int = Field(default=100, description="Requests per minute")
    rate_limit_window: int = Field(default=60, description="Rate limiting window in seconds")
    
    # Request Configuration
    max_request_size: int = Field(default=1024 * 1024, description="Max request size in bytes")
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def get_cors_config(self) -> dict:
        """Get CORS configuration dictionary."""
        return {
            "allow_origins": self.cors_origins,
            "allow_credentials": self.cors_allow_credentials,
            "allow_methods": self.cors_allow_methods,
            "allow_headers": self.cors_allow_headers,
        }
    
    def get_database_url(self) -> str:
        """Get database connection URL."""
        return f"file://{self.chroma_persist_directory}"
    
    def is_groq_enabled(self) -> bool:
        """Check if Groq is enabled."""
        if self.use_groq == "false":
            return False
        elif self.use_groq == "true":
            return bool(self.groq_api_key)
        else:  # auto
            return bool(self.groq_api_key)
    
    def get_retrieval_config(self) -> dict:
        """Get retrieval configuration."""
        return {
            "dense_weight": self.dense_weight,
            "sparse_weight": self.sparse_weight,
            "top_k": self.top_k,
            "enable_reranking": self.enable_reranking,
            "rerank_top_k": self.rerank_top_k,
            "persist_directory": self.chroma_persist_directory,
        }
    
    def get_generation_config(self) -> dict:
        """Get generation configuration."""
        return {
            "use_groq": self.use_groq,
            "groq_model": self.groq_model,
            "groq_temperature": self.groq_temperature,
            "groq_max_tokens": self.groq_max_tokens,
            "confidence_threshold": self.confidence_threshold,
        }


# Global configuration instance
config = BackendConfig()
