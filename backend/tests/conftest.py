"""
Pytest configuration and fixtures for RAG Chatbot tests.

This module provides shared fixtures and configuration for all tests.
"""

import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.core.config import Settings
from app.main import app
from app.services.factory import ServiceFactory


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings with safe defaults."""
    return Settings(
        environment="test",
        app_name="RAG Chatbot Test",
        app_version="0.1.0-test",
        
        # Database settings
        database__url="sqlite:///test.db",
        database__echo=False,
        
        # Redis settings  
        redis__url="redis://localhost:6379/1",
        
        # OpenAI settings (use dummy values)
        openai__api_key="test-api-key",
        openai__model="gpt-3.5-turbo",
        openai__embedding_model="text-embedding-ada-002",
        
        # Pinecone settings (use dummy values)
        pinecone__api_key="test-pinecone-key",
        pinecone__environment="test-env",
        pinecone__index_name="test-index",
        
        # Security settings
        security__secret_key="test-secret-key",
        security__allowed_api_keys=["test-api-key"],
        
        # Logging settings
        logging__level="DEBUG",
        logging__format="text",
    )


@pytest.fixture
def client() -> TestClient:
    """Create FastAPI test client."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_openai_provider():
    """Mock OpenAI provider for testing."""
    mock = AsyncMock()
    mock.generate_response.return_value = MagicMock(
        content="Test response",
        model="gpt-3.5-turbo",
        usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        metadata={"finish_reason": "stop", "cost_usd": 0.001, "duration_ms": 100}
    )
    mock.count_tokens.return_value = 10
    mock.get_available_models.return_value = ["gpt-3.5-turbo", "gpt-4"]
    mock.validate_connection.return_value = True
    return mock


@pytest.fixture
def mock_openai_embeddings():
    """Mock OpenAI embeddings service for testing."""
    mock = AsyncMock()
    mock.embed_text.return_value = MagicMock(
        embedding=[0.1] * 1536,
        model="text-embedding-ada-002",
        usage={"total_tokens": 5, "prompt_tokens": 5}
    )
    mock.embed_texts.return_value = [
        MagicMock(
            embedding=[0.1] * 1536,
            model="text-embedding-ada-002",
            usage={"total_tokens": 5, "prompt_tokens": 5}
        )
    ]
    mock.get_embedding_dimension.return_value = 1536
    mock.validate_connection.return_value = True
    return mock


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing."""
    mock = AsyncMock()
    mock.add_documents.return_value = ["doc1", "doc2"]
    mock.search.return_value = []
    mock.delete_documents.return_value = True
    mock.update_document.return_value = True
    mock.get_document.return_value = None
    mock.list_documents.return_value = []
    mock.get_stats.return_value = {"total_documents": 0, "total_vectors": 0}
    mock.validate_connection.return_value = True
    return mock


@pytest.fixture
def mock_retrieval_strategy():
    """Mock retrieval strategy for testing."""
    mock = AsyncMock()
    mock.retrieve.return_value = []
    mock.get_strategy_name.return_value = "test_strategy"
    return mock


@pytest.fixture
def mock_chat_service():
    """Mock chat service for testing."""
    mock = AsyncMock()
    mock.chat.return_value = {
        "response": "Test response",
        "sources": [],
        "conversation_id": "test-conv-123",
        "metadata": {}
    }
    mock.get_conversation_history.return_value = []
    mock.clear_conversation.return_value = True
    return mock


@pytest.fixture(autouse=True)
def clear_service_factory():
    """Clear ServiceFactory instances between tests."""
    yield
    ServiceFactory.clear_instances()


@pytest.fixture
def sample_document_content():
    """Sample document content for testing."""
    return """
    This is a sample document for testing the RAG system.
    It contains multiple paragraphs with various information.
    
    The system should be able to process this text, create embeddings,
    and store it in the vector database for retrieval during conversations.
    
    This document serves as test data for validating the document processing
    pipeline and retrieval mechanisms.
    """


@pytest.fixture
def sample_chat_messages():
    """Sample chat messages for testing."""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"},
        {"role": "assistant", "content": "The capital of France is Paris."},
        {"role": "user", "content": "Tell me more about it."},
    ]


@pytest.fixture
def sample_embedding():
    """Sample embedding vector for testing."""
    return [0.1 * i for i in range(1536)]


@pytest.fixture
def sample_search_results():
    """Sample search results for testing."""
    from app.services.base import Document, SearchResult
    
    return [
        SearchResult(
            document=Document(
                id="doc1",
                content="Sample document content",
                metadata={"source": "test.txt", "page": 1},
                source="test.txt"
            ),
            score=0.95,
            relevance_score=0.9
        ),
        SearchResult(
            document=Document(
                id="doc2", 
                content="Another document content",
                metadata={"source": "test2.txt", "page": 1},
                source="test2.txt"
            ),
            score=0.85,
            relevance_score=0.8
        )
    ]


# Mark all tests as asyncio by default
pytestmark = pytest.mark.asyncio
