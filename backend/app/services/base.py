"""
Abstract base classes for all external services.

This module defines the interfaces that all service implementations must follow,
enabling the Strategy pattern for easy component swapping.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


class Document(BaseModel):
    """Document model for storing text content with metadata."""
    
    id: str
    content: str
    metadata: Dict[str, Any] = {}
    source: Optional[str] = None
    page_number: Optional[int] = None
    chunk_index: Optional[int] = None


class SearchResult(BaseModel):
    """Search result from vector store."""
    
    document: Document
    score: float
    relevance_score: Optional[float] = None


class LLMResponse(BaseModel):
    """Response from language model."""
    
    content: str
    model: str
    usage: Dict[str, int] = {}
    metadata: Dict[str, Any] = {}


class EmbeddingResponse(BaseModel):
    """Response from embedding service."""
    
    embedding: List[float]
    model: str
    usage: Dict[str, int] = {}


class LLMProvider(ABC):
    """Abstract base class for language model providers."""
    
    def __init__(self, **kwargs):
        """Initialize the LLM provider."""
        pass
    
    @abstractmethod
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[LLMResponse, Any]:
        """
        Generate response from language model.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model name to use (optional)
            max_tokens: Maximum tokens in response
            temperature: Response randomness (0.0 to 1.0)
            stream: Whether to stream response
            **kwargs: Additional provider-specific parameters
        
        Returns:
            LLMResponse object or stream generator
        """
        pass
    
    @abstractmethod
    async def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """
        Count tokens in text for the specified model.
        
        Args:
            text: Text to count tokens for
            model: Model name for tokenization
        
        Returns:
            Number of tokens
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """
        Get list of available models.
        
        Returns:
            List of available model names
        """
        pass
    
    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        Validate connection to the LLM service.
        
        Returns:
            True if connection is valid
        """
        pass


class EmbeddingsService(ABC):
    """Abstract base class for embedding services."""
    
    def __init__(self, **kwargs):
        """Initialize the embeddings service."""
        pass
    
    @abstractmethod
    async def embed_text(
        self,
        text: str,
        model: Optional[str] = None,
        **kwargs
    ) -> EmbeddingResponse:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            model: Model name to use (optional)
            **kwargs: Additional provider-specific parameters
        
        Returns:
            EmbeddingResponse with embedding vector
        """
        pass
    
    @abstractmethod
    async def embed_texts(
        self,
        texts: List[str],
        model: Optional[str] = None,
        batch_size: int = 100,
        **kwargs
    ) -> List[EmbeddingResponse]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            model: Model name to use (optional)
            batch_size: Batch size for processing
            **kwargs: Additional provider-specific parameters
        
        Returns:
            List of EmbeddingResponse objects
        """
        pass
    
    @abstractmethod
    def get_embedding_dimension(self, model: Optional[str] = None) -> int:
        """
        Get embedding dimension for the model.
        
        Args:
            model: Model name
        
        Returns:
            Embedding vector dimension
        """
        pass
    
    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        Validate connection to the embedding service.
        
        Returns:
            True if connection is valid
        """
        pass


class VectorStore(ABC):
    """Abstract base class for vector databases."""
    
    def __init__(self, **kwargs):
        """Initialize the vector store."""
        pass
    
    @abstractmethod
    async def add_documents(
        self,
        documents: List[Document],
        embeddings: List[List[float]],
        **kwargs
    ) -> List[str]:
        """
        Add documents with embeddings to the vector store.
        
        Args:
            documents: List of documents to add
            embeddings: List of embedding vectors
            **kwargs: Additional store-specific parameters
        
        Returns:
            List of document IDs
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[SearchResult]:
        """
        Search for similar documents.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filter_metadata: Metadata filters to apply
            **kwargs: Additional search parameters
        
        Returns:
            List of SearchResult objects
        """
        pass
    
    @abstractmethod
    async def delete_documents(
        self,
        document_ids: List[str],
        **kwargs
    ) -> bool:
        """
        Delete documents from the vector store.
        
        Args:
            document_ids: List of document IDs to delete
            **kwargs: Additional parameters
        
        Returns:
            True if deletion was successful
        """
        pass
    
    @abstractmethod
    async def update_document(
        self,
        document_id: str,
        document: Document,
        embedding: List[float],
        **kwargs
    ) -> bool:
        """
        Update a document in the vector store.
        
        Args:
            document_id: ID of document to update
            document: Updated document
            embedding: Updated embedding vector
            **kwargs: Additional parameters
        
        Returns:
            True if update was successful
        """
        pass
    
    @abstractmethod
    async def get_document(
        self,
        document_id: str,
        **kwargs
    ) -> Optional[Document]:
        """
        Retrieve a document by ID.
        
        Args:
            document_id: Document ID
            **kwargs: Additional parameters
        
        Returns:
            Document if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def list_documents(
        self,
        filter_metadata: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        **kwargs
    ) -> List[Document]:
        """
        List documents in the vector store.
        
        Args:
            filter_metadata: Metadata filters to apply
            limit: Maximum number of documents to return
            **kwargs: Additional parameters
        
        Returns:
            List of documents
        """
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector store.
        
        Returns:
            Dictionary with store statistics
        """
        pass
    
    @abstractmethod
    async def validate_connection(self) -> bool:
        """
        Validate connection to the vector store.
        
        Returns:
            True if connection is valid
        """
        pass


class RetrievalStrategy(ABC):
    """Abstract base class for retrieval strategies."""
    
    def __init__(self, vector_store: VectorStore, embeddings_service: EmbeddingsService):
        """Initialize the retrieval strategy."""
        self.vector_store = vector_store
        self.embeddings_service = embeddings_service
    
    @abstractmethod
    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[SearchResult]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: Search query
            top_k: Number of results to return
            filter_metadata: Metadata filters to apply
            **kwargs: Additional strategy-specific parameters
        
        Returns:
            List of SearchResult objects
        """
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """
        Get the name of this retrieval strategy.
        
        Returns:
            Strategy name
        """
        pass


class ChatService(ABC):
    """Abstract base class for chat orchestration services."""
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        retrieval_strategy: RetrievalStrategy,
        **kwargs
    ):
        """Initialize the chat service."""
        self.llm_provider = llm_provider
        self.retrieval_strategy = retrieval_strategy
    
    @abstractmethod
    async def chat(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process a chat message and generate response.
        
        Args:
            message: User message
            conversation_id: Conversation identifier
            context: Additional context information
            **kwargs: Additional parameters
        
        Returns:
            Chat response with sources and metadata
        """
        pass
    
    @abstractmethod
    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history.
        
        Args:
            conversation_id: Conversation identifier
            limit: Maximum number of messages to return
        
        Returns:
            List of conversation messages
        """
        pass
    
    @abstractmethod
    async def clear_conversation(self, conversation_id: str) -> bool:
        """
        Clear conversation history.
        
        Args:
            conversation_id: Conversation identifier
        
        Returns:
            True if successful
        """
        pass
