"""
Configuration management using Pydantic Settings.

This module provides centralized configuration management with environment variable support,
YAML file loading, and type validation.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    url: str = Field(
        default="postgresql://postgres:password@localhost:5432/rag_chatbot",
        description="Database connection URL"
    )
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Max overflow connections")
    echo: bool = Field(default=False, description="Enable SQL query logging")
    
    model_config = ConfigDict(env_prefix="DB_")


class RedisSettings(BaseSettings):
    """Redis cache configuration settings."""
    
    url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    ttl: int = Field(default=3600, description="Default TTL in seconds")
    
    model_config = ConfigDict(env_prefix="REDIS_")


class OpenAISettings(BaseSettings):
    """OpenAI API configuration settings."""
    
    api_key: str = Field(default="test-key", description="OpenAI API key")
    model: str = Field(default="gpt-4", description="Default model to use")
    embedding_model: str = Field(
        default="text-embedding-ada-002", 
        description="Embedding model"
    )
    max_tokens: int = Field(default=1000, description="Max tokens per response")
    temperature: float = Field(default=0.7, description="Response temperature")
    
    model_config = ConfigDict(env_prefix="OPENAI_")


class PineconeSettings(BaseSettings):
    """Pinecone vector database configuration settings."""
    
    api_key: str = Field(default="test-key", description="Pinecone API key")
    environment: str = Field(default="test-env", description="Pinecone environment")
    index_name: str = Field(default="rag-chatbot", description="Index name")
    dimension: int = Field(default=1536, description="Vector dimension")
    metric: str = Field(default="cosine", description="Distance metric")
    
    model_config = ConfigDict(env_prefix="PINECONE_")


class ChromaDBSettings(BaseSettings):
    """ChromaDB local vector database configuration settings."""
    
    persist_directory: str = Field(
        default="./data/chromadb", 
        description="ChromaDB persistence directory"
    )
    collection_name: str = Field(
        default="rag-chatbot", 
        description="Collection name"
    )
    
    model_config = ConfigDict(env_prefix="CHROMADB_")


class APISettings(BaseSettings):
    """API server configuration settings."""
    
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    reload: bool = Field(default=False, description="Auto-reload on changes")
    workers: int = Field(default=1, description="Number of worker processes")
    
    # CORS settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000"], 
        description="Allowed CORS origins"
    )
    cors_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE"], 
        description="Allowed CORS methods"
    )
    cors_headers: List[str] = Field(
        default=["*"], 
        description="Allowed CORS headers"
    )
    
    # Rate limiting
    rate_limit_requests: int = Field(
        default=100, 
        description="Rate limit requests per minute"
    )
    
    model_config = ConfigDict(env_prefix="API_")


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""
    
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="json", description="Log format (json|text)")
    file: Optional[str] = Field(default=None, description="Log file path")
    max_size: int = Field(default=10485760, description="Max log file size (10MB)")
    backup_count: int = Field(default=5, description="Number of backup files")
    
    model_config = ConfigDict(env_prefix="LOG_")


class SecuritySettings(BaseSettings):
    """Security configuration settings."""
    
    secret_key: str = Field(default="test-secret-key", description="Application secret key")
    api_key_header: str = Field(
        default="X-API-Key", 
        description="API key header name"
    )
    allowed_api_keys: List[str] = Field(
        default=[], 
        description="List of allowed API keys"
    )
    
    model_config = ConfigDict(env_prefix="SECURITY_")


class Settings(BaseSettings):
    """Main application settings."""
    
    # Application info
    app_name: str = Field(default="RAG Chatbot", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(default="development", description="Environment")
    
    # Component settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    pinecone: PineconeSettings = Field(default_factory=PineconeSettings)
    chromadb: ChromaDBSettings = Field(default_factory=ChromaDBSettings)
    api: APISettings = Field(default_factory=APISettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    
    # Service configuration
    vector_store_provider: str = Field(
        default="pinecone", 
        description="Vector store provider (pinecone|chromadb)"
    )
    llm_provider: str = Field(
        default="openai", 
        description="LLM provider (openai|anthropic)"
    )
    embeddings_provider: str = Field(
        default="openai", 
        description="Embeddings provider"
    )
    
    # Document processing
    chunk_size: int = Field(default=1000, description="Text chunk size")
    chunk_overlap: int = Field(default=200, description="Text chunk overlap")
    max_document_size: int = Field(
        default=10485760, 
        description="Max document size (10MB)"
    )
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment setting."""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v
    
    @field_validator("vector_store_provider")
    @classmethod
    def validate_vector_store_provider(cls, v):
        """Validate vector store provider."""
        allowed = ["pinecone", "chromadb"]
        if v not in allowed:
            raise ValueError(f"Vector store provider must be one of: {allowed}")
        return v
    
    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, v):
        """Validate LLM provider."""
        allowed = ["openai", "anthropic"]
        if v not in allowed:
            raise ValueError(f"LLM provider must be one of: {allowed}")
        return v
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="__"
    )


def load_yaml_config(config_path: Union[str, Path]) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    config_path = Path(config_path)
    if not config_path.exists():
        return {}
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_settings() -> Settings:
    """Get application settings with YAML override support."""
    # Load base settings from environment
    settings = Settings()
    
    # Look for YAML config files
    config_dir = Path("config")
    yaml_configs = [
        config_dir / "config.yaml",
        config_dir / f"config.{settings.environment}.yaml",
    ]
    
    # Merge YAML configurations
    yaml_config = {}
    for config_file in yaml_configs:
        if config_file.exists():
            file_config = load_yaml_config(config_file)
            yaml_config.update(file_config)
    
    # Override settings with YAML config if provided
    if yaml_config:
        # Convert flat YAML to nested structure for Pydantic
        settings_dict = settings.model_dump()
        _merge_yaml_config(settings_dict, yaml_config)
        settings = Settings(**settings_dict)
    
    return settings


def _merge_yaml_config(settings_dict: Dict[str, Any], yaml_config: Dict[str, Any]) -> None:
    """Merge YAML config into settings dictionary."""
    for key, value in yaml_config.items():
        if isinstance(value, dict) and key in settings_dict:
            if isinstance(settings_dict[key], dict):
                _merge_yaml_config(settings_dict[key], value)
            else:
                # For Pydantic model instances, update the dict representation
                if hasattr(settings_dict[key], 'model_dump'):
                    model_dict = settings_dict[key].model_dump()
                    _merge_yaml_config(model_dict, value)
                    settings_dict[key] = model_dict
        else:
            settings_dict[key] = value


# Global settings instance
settings = get_settings()
