"""
Service factory for creating and managing service instances.

This module implements the Factory pattern to create appropriate service instances
based on configuration, enabling easy component swapping and dependency injection.
"""

from typing import Dict, Optional, Type, Any

from ..core.config import settings
from ..core.logging import get_logger
from .base import LLMProvider, EmbeddingsService, VectorStore, RetrievalStrategy, ChatService

logger = get_logger(__name__)


class ServiceFactory:
    """Factory class for creating service instances."""
    
    # Registry of available implementations
    _llm_providers: Dict[str, Type[LLMProvider]] = {}
    _embeddings_services: Dict[str, Type[EmbeddingsService]] = {}
    _vector_stores: Dict[str, Type[VectorStore]] = {}
    _retrieval_strategies: Dict[str, Type[RetrievalStrategy]] = {}
    _chat_services: Dict[str, Type[ChatService]] = {}
    
    # Singleton instances
    _instances: Dict[str, Any] = {}
    
    @classmethod
    def register_llm_provider(cls, name: str, provider_class: Type[LLMProvider]) -> None:
        """Register an LLM provider implementation."""
        cls._llm_providers[name] = provider_class
        logger.info(f"Registered LLM provider: {name}")
    
    @classmethod
    def register_embeddings_service(cls, name: str, service_class: Type[EmbeddingsService]) -> None:
        """Register an embeddings service implementation."""
        cls._embeddings_services[name] = service_class
        logger.info(f"Registered embeddings service: {name}")
    
    @classmethod
    def register_vector_store(cls, name: str, store_class: Type[VectorStore]) -> None:
        """Register a vector store implementation."""
        cls._vector_stores[name] = store_class
        logger.info(f"Registered vector store: {name}")
    
    @classmethod
    def register_retrieval_strategy(cls, name: str, strategy_class: Type[RetrievalStrategy]) -> None:
        """Register a retrieval strategy implementation."""
        cls._retrieval_strategies[name] = strategy_class
        logger.info(f"Registered retrieval strategy: {name}")
    
    @classmethod
    def register_chat_service(cls, name: str, service_class: Type[ChatService]) -> None:
        """Register a chat service implementation."""
        cls._chat_services[name] = service_class
        logger.info(f"Registered chat service: {name}")
    
    @classmethod
    def create_llm_provider(
        cls,
        provider_name: Optional[str] = None,
        **kwargs
    ) -> LLMProvider:
        """Create an LLM provider instance."""
        provider_name = provider_name or settings.llm_provider
        
        if provider_name not in cls._llm_providers:
            available = list(cls._llm_providers.keys())
            raise ValueError(
                f"Unknown LLM provider: {provider_name}. "
                f"Available providers: {available}"
            )
        
        provider_class = cls._llm_providers[provider_name]
        instance = provider_class(**kwargs)
        
        logger.info(f"Created LLM provider: {provider_name}")
        return instance
    
    @classmethod
    def create_embeddings_service(
        cls,
        service_name: Optional[str] = None,
        **kwargs
    ) -> EmbeddingsService:
        """Create an embeddings service instance."""
        service_name = service_name or settings.embeddings_provider
        
        if service_name not in cls._embeddings_services:
            available = list(cls._embeddings_services.keys())
            raise ValueError(
                f"Unknown embeddings service: {service_name}. "
                f"Available services: {available}"
            )
        
        service_class = cls._embeddings_services[service_name]
        instance = service_class(**kwargs)
        
        logger.info(f"Created embeddings service: {service_name}")
        return instance
    
    @classmethod
    def create_vector_store(
        cls,
        store_name: Optional[str] = None,
        **kwargs
    ) -> VectorStore:
        """Create a vector store instance."""
        store_name = store_name or settings.vector_store_provider
        
        if store_name not in cls._vector_stores:
            available = list(cls._vector_stores.keys())
            raise ValueError(
                f"Unknown vector store: {store_name}. "
                f"Available stores: {available}"
            )
        
        store_class = cls._vector_stores[store_name]
        instance = store_class(**kwargs)
        
        logger.info(f"Created vector store: {store_name}")
        return instance
    
    @classmethod
    def create_retrieval_strategy(
        cls,
        strategy_name: str = "similarity",
        vector_store: Optional[VectorStore] = None,
        embeddings_service: Optional[EmbeddingsService] = None,
        **kwargs
    ) -> RetrievalStrategy:
        """Create a retrieval strategy instance."""
        if strategy_name not in cls._retrieval_strategies:
            available = list(cls._retrieval_strategies.keys())
            raise ValueError(
                f"Unknown retrieval strategy: {strategy_name}. "
                f"Available strategies: {available}"
            )
        
        # Create dependencies if not provided
        if vector_store is None:
            vector_store = cls.get_vector_store()
        if embeddings_service is None:
            embeddings_service = cls.get_embeddings_service()
        
        strategy_class = cls._retrieval_strategies[strategy_name]
        instance = strategy_class(
            vector_store=vector_store,
            embeddings_service=embeddings_service,
            **kwargs
        )
        
        logger.info(f"Created retrieval strategy: {strategy_name}")
        return instance
    
    @classmethod
    def create_chat_service(
        cls,
        service_name: str = "default",
        llm_provider: Optional[LLMProvider] = None,
        retrieval_strategy: Optional[RetrievalStrategy] = None,
        **kwargs
    ) -> ChatService:
        """Create a chat service instance."""
        if service_name not in cls._chat_services:
            available = list(cls._chat_services.keys())
            raise ValueError(
                f"Unknown chat service: {service_name}. "
                f"Available services: {available}"
            )
        
        # Create dependencies if not provided
        if llm_provider is None:
            llm_provider = cls.get_llm_provider()
        if retrieval_strategy is None:
            retrieval_strategy = cls.get_retrieval_strategy()
        
        service_class = cls._chat_services[service_name]
        instance = service_class(
            llm_provider=llm_provider,
            retrieval_strategy=retrieval_strategy,
            **kwargs
        )
        
        logger.info(f"Created chat service: {service_name}")
        return instance
    
    @classmethod
    def get_llm_provider(cls, provider_name: Optional[str] = None) -> LLMProvider:
        """Get or create singleton LLM provider instance."""
        provider_name = provider_name or settings.llm_provider
        cache_key = f"llm_provider_{provider_name}"
        
        if cache_key not in cls._instances:
            cls._instances[cache_key] = cls.create_llm_provider(provider_name)
        
        return cls._instances[cache_key]
    
    @classmethod
    def get_embeddings_service(cls, service_name: Optional[str] = None) -> EmbeddingsService:
        """Get or create singleton embeddings service instance."""
        service_name = service_name or settings.embeddings_provider
        cache_key = f"embeddings_service_{service_name}"
        
        if cache_key not in cls._instances:
            cls._instances[cache_key] = cls.create_embeddings_service(service_name)
        
        return cls._instances[cache_key]
    
    @classmethod
    def get_vector_store(cls, store_name: Optional[str] = None) -> VectorStore:
        """Get or create singleton vector store instance."""
        store_name = store_name or settings.vector_store_provider
        cache_key = f"vector_store_{store_name}"
        
        if cache_key not in cls._instances:
            cls._instances[cache_key] = cls.create_vector_store(store_name)
        
        return cls._instances[cache_key]
    
    @classmethod
    def get_retrieval_strategy(cls, strategy_name: str = "similarity") -> RetrievalStrategy:
        """Get or create singleton retrieval strategy instance."""
        cache_key = f"retrieval_strategy_{strategy_name}"
        
        if cache_key not in cls._instances:
            cls._instances[cache_key] = cls.create_retrieval_strategy(strategy_name)
        
        return cls._instances[cache_key]
    
    @classmethod
    def get_chat_service(cls, service_name: str = "default") -> ChatService:
        """Get or create singleton chat service instance."""
        cache_key = f"chat_service_{service_name}"
        
        if cache_key not in cls._instances:
            cls._instances[cache_key] = cls.create_chat_service(service_name)
        
        return cls._instances[cache_key]
    
    @classmethod
    def clear_instances(cls) -> None:
        """Clear all cached instances."""
        cls._instances.clear()
        logger.info("Cleared all service instances")
    
    @classmethod
    def get_available_providers(cls) -> Dict[str, list]:
        """Get all available service providers."""
        return {
            "llm_providers": list(cls._llm_providers.keys()),
            "embeddings_services": list(cls._embeddings_services.keys()),
            "vector_stores": list(cls._vector_stores.keys()),
            "retrieval_strategies": list(cls._retrieval_strategies.keys()),
            "chat_services": list(cls._chat_services.keys()),
        }
    
    @classmethod
    async def validate_all_connections(cls) -> Dict[str, bool]:
        """Validate connections for all configured services."""
        results = {}
        
        try:
            llm_provider = cls.get_llm_provider()
            results["llm_provider"] = await llm_provider.validate_connection()
        except Exception as e:
            logger.error(f"Failed to validate LLM provider: {e}")
            results["llm_provider"] = False
        
        try:
            embeddings_service = cls.get_embeddings_service()
            results["embeddings_service"] = await embeddings_service.validate_connection()
        except Exception as e:
            logger.error(f"Failed to validate embeddings service: {e}")
            results["embeddings_service"] = False
        
        try:
            vector_store = cls.get_vector_store()
            results["vector_store"] = await vector_store.validate_connection()
        except Exception as e:
            logger.error(f"Failed to validate vector store: {e}")
            results["vector_store"] = False
        
        return results


# Auto-register implementations when they're available
def auto_register_services():
    """Automatically register service implementations."""
    try:
        from .llm.openai_provider import OpenAIProvider
        ServiceFactory.register_llm_provider("openai", OpenAIProvider)
    except ImportError:
        logger.debug("OpenAI provider not available")
    
    try:
        from .embeddings.openai_embeddings import OpenAIEmbeddings
        ServiceFactory.register_embeddings_service("openai", OpenAIEmbeddings)
    except ImportError:
        logger.debug("OpenAI embeddings not available")
    
    try:
        from .vectorstore.pinecone_store import PineconeStore
        ServiceFactory.register_vector_store("pinecone", PineconeStore)
    except ImportError:
        logger.debug("Pinecone store not available")
    
    try:
        from .vectorstore.chromadb_store import ChromaDBStore
        ServiceFactory.register_vector_store("chromadb", ChromaDBStore)
    except ImportError:
        logger.debug("ChromaDB store not available")
    
    try:
        from .retrieval.similarity_strategy import SimilarityStrategy
        ServiceFactory.register_retrieval_strategy("similarity", SimilarityStrategy)
    except ImportError:
        logger.debug("Similarity strategy not available")
    
    try:
        from .chat.default_chat_service import DefaultChatService
        ServiceFactory.register_chat_service("default", DefaultChatService)
    except ImportError:
        logger.debug("Default chat service not available")


# Register services on import
auto_register_services()
