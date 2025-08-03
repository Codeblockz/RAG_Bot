"""
Unit tests for configuration management.
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from app.core.config import Settings, load_yaml_config, get_settings


class TestSettings:
    """Test Settings class functionality."""
    
    def test_default_settings(self, monkeypatch):
        """Test default settings creation."""
        # Set environment variables for nested settings
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("PINECONE_API_KEY", "test-key")
        monkeypatch.setenv("PINECONE_ENVIRONMENT", "test-env")
        monkeypatch.setenv("SECURITY_SECRET_KEY", "test-secret")
        
        settings = Settings()
        
        assert settings.app_name == "RAG Chatbot"
        assert settings.app_version == "0.1.0"
        assert settings.environment == "development"
        assert settings.openai.api_key == "test-key"
        assert settings.vector_store_provider == "pinecone"
        assert settings.llm_provider == "openai"
    
    def test_environment_validation(self):
        """Test environment validation."""
        with pytest.raises(ValueError, match="Environment must be one of"):
            Settings(environment="invalid")
    
    def test_vector_store_provider_validation(self):
        """Test vector store provider validation."""
        with pytest.raises(ValueError, match="Vector store provider must be one of"):
            Settings(vector_store_provider="invalid")
    
    def test_llm_provider_validation(self):
        """Test LLM provider validation."""
        with pytest.raises(ValueError, match="LLM provider must be one of"):
            Settings(llm_provider="invalid")


class TestYamlConfig:
    """Test YAML configuration loading."""
    
    def test_load_yaml_config_existing_file(self):
        """Test loading existing YAML config file."""
        config_data = {
            "api": {
                "host": "127.0.0.1",
                "port": 9000
            },
            "openai": {
                "model": "gpt-4",
                "temperature": 0.5
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            loaded_config = load_yaml_config(temp_path)
            assert loaded_config == config_data
        finally:
            os.unlink(temp_path)
    
    def test_load_yaml_config_nonexistent_file(self):
        """Test loading non-existent YAML config file."""
        config = load_yaml_config("nonexistent.yaml")
        assert config == {}
    
    def test_load_yaml_config_empty_file(self):
        """Test loading empty YAML config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")
            temp_path = f.name
        
        try:
            config = load_yaml_config(temp_path)
            assert config == {}
        finally:
            os.unlink(temp_path)


class TestGetSettings:
    """Test get_settings function."""
    
    def test_get_settings_without_yaml(self, monkeypatch):
        """Test get_settings without YAML files."""
        # Set required environment variables
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("PINECONE_API_KEY", "test-key")
        monkeypatch.setenv("PINECONE_ENVIRONMENT", "test-env")
        monkeypatch.setenv("SECURITY_SECRET_KEY", "test-secret")
        
        settings = get_settings()
        assert settings.app_name == "RAG Chatbot"
        assert settings.openai.api_key == "test-key"
    
    def test_get_settings_with_yaml_override(self, monkeypatch):
        """Test get_settings with YAML configuration override."""
        # Set required environment variables
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        monkeypatch.setenv("PINECONE_API_KEY", "test-key")
        monkeypatch.setenv("PINECONE_ENVIRONMENT", "test-env")
        monkeypatch.setenv("SECURITY_SECRET_KEY", "test-secret")
        
        # Create temporary config directory and file
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "config"
            config_dir.mkdir()
            config_file = config_dir / "config.yaml"
            
            config_data = {
                "app_name": "Test RAG Chatbot",
                "openai": {
                    "model": "gpt-4",
                    "temperature": 0.5
                }
            }
            
            with open(config_file, 'w') as f:
                yaml.dump(config_data, f)
            
            # Change to temp directory to test config loading
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                settings = get_settings()
                
                # Check that YAML overrides work
                assert settings.app_name == "Test RAG Chatbot"
                assert settings.openai.model == "gpt-4"
                assert settings.openai.temperature == 0.5
                
                # Check that env vars still work for non-overridden values
                assert settings.openai.api_key == "env-key"
            finally:
                os.chdir(original_cwd)


class TestDatabaseSettings:
    """Test DatabaseSettings class."""
    
    def test_database_settings_defaults(self):
        """Test database settings default values."""
        from app.core.config import DatabaseSettings
        
        db_settings = DatabaseSettings()
        assert "postgresql://" in db_settings.url
        assert db_settings.pool_size == 10
        assert db_settings.max_overflow == 20
        assert db_settings.echo is False
    
    def test_database_settings_env_prefix(self, monkeypatch):
        """Test database settings environment variable prefix."""
        from app.core.config import DatabaseSettings
        
        monkeypatch.setenv("DB_URL", "postgresql://test:test@localhost/test")
        monkeypatch.setenv("DB_POOL_SIZE", "5")
        monkeypatch.setenv("DB_ECHO", "true")
        
        db_settings = DatabaseSettings()
        assert db_settings.url == "postgresql://test:test@localhost/test"
        assert db_settings.pool_size == 5
        assert db_settings.echo is True


class TestOpenAISettings:
    """Test OpenAISettings class."""
    
    def test_openai_settings_defaults(self):
        """Test OpenAI settings default values."""
        from app.core.config import OpenAISettings
        
        settings = OpenAISettings()
        assert settings.api_key == "test-key"  # Default value for development
        assert settings.model == "gpt-4"
        assert settings.embedding_model == "text-embedding-ada-002"
    
    def test_openai_settings_with_key(self):
        """Test OpenAI settings with API key."""
        from app.core.config import OpenAISettings
        
        settings = OpenAISettings(api_key="test-key")
        assert settings.api_key == "test-key"
        assert settings.model == "gpt-4"
        assert settings.embedding_model == "text-embedding-ada-002"
        assert settings.max_tokens == 1000
        assert settings.temperature == 0.7


class TestPineconeSettings:
    """Test PineconeSettings class."""
    
    def test_pinecone_settings_defaults(self):
        """Test Pinecone settings default values."""
        from app.core.config import PineconeSettings
        
        settings = PineconeSettings()
        assert settings.api_key == "test-key"  # Default value for development  
        assert settings.environment == "test-env"  # Default value for development
        assert settings.index_name == "rag-chatbot"
        assert settings.dimension == 1536
        assert settings.metric == "cosine"
    
    def test_pinecone_settings_with_required_fields(self):
        """Test Pinecone settings with required fields."""
        from app.core.config import PineconeSettings
        
        settings = PineconeSettings(
            api_key="test-key",
            environment="test-env"
        )
        assert settings.api_key == "test-key"
        assert settings.environment == "test-env"
        assert settings.index_name == "rag-chatbot"
        assert settings.dimension == 1536
        assert settings.metric == "cosine"
