"""
Configuration management for the Mutual Fund FAQ Assistant.
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional

import yaml
from pydantic_settings import BaseSettings
from pydantic import Field


class AppConfig(BaseSettings):
    """Application configuration with environment variable support."""
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_debug: bool = Field(default=False, env="API_DEBUG")
    cors_origins: List[str] = Field(default=["http://localhost:3000"], env="CORS_ORIGINS")
    
    # LLM Configuration
    groq_api_key: str = Field(..., env="GROQ_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    
    # Database Configuration
    chroma_persist_directory: str = Field(default="./data/vectorstore", env="CHROMA_PERSIST_DIRECTORY")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="./logs/app.log", env="LOG_FILE")
    
    # Cache Configuration
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")
    cache_max_size: int = Field(default=1000, env="CACHE_MAX_SIZE")
    
    # Monitoring Configuration
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    
    # Security
    secret_key: str = Field(..., env="SECRET_KEY")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class ConfigManager:
    """Manages configuration files and settings."""
    
    def __init__(self, config_dir: str = "configs"):
        self.config_dir = Path(config_dir)
        self.app_config = AppConfig()
        
    def load_sources(self) -> Dict[str, Any]:
        """Load approved sources configuration."""
        sources_file = self.config_dir / "sources.yaml"
        with open(sources_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def load_refusal_intents(self) -> Dict[str, Any]:
        """Load refusal intents configuration."""
        refusal_file = self.config_dir / "refusal_intents.yaml"
        with open(refusal_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def load_disclaimer(self) -> str:
        """Load disclaimer text."""
        disclaimer_file = self.config_dir / "disclaimer.txt"
        with open(disclaimer_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    
    def load_app_config(self) -> Dict[str, Any]:
        """Load application configuration."""
        app_config_file = self.config_dir / "app_config.yaml"
        with open(app_config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def get_whitelisted_urls(self) -> List[str]:
        """Get list of whitelisted URLs."""
        sources = self.load_sources()
        urls = []
        for scheme in sources.get('schemes', []):
            for source in scheme.get('sources', []):
                urls.append(source['url'])
        return urls
    
    def get_scheme_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get scheme information by URL."""
        sources = self.load_sources()
        for scheme in sources.get('schemes', []):
            for source in scheme.get('sources', []):
                if source['url'] == url:
                    return scheme
        return None


# Global configuration instance
config_manager = ConfigManager()
app_config = config_manager.app_config
