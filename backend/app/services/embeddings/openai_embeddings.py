"""
OpenAI embeddings service implementation.

This module provides OpenAI embeddings integration following the EmbeddingsService interface.
"""

import asyncio
import time
from typing import List, Optional

from openai import AsyncOpenAI

from ...core.config import settings
from ...core.logging import get_logger
from ..base import EmbeddingsService, EmbeddingResponse


class OpenAIEmbeddings(EmbeddingsService):
    """OpenAI embeddings service implementation."""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """Initialize OpenAI embeddings service."""
        self.api_key = api_key or settings.openai.api_key
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.logger = get_logger(self.__class__.__name__)
        
        # Model configuration
        self.default_model = settings.openai.embedding_model
        
        # Model dimensions
        self.model_dimensions = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
        }
        
        # Token pricing (approximate, in USD per 1K tokens)
        self.token_pricing = {
            "text-embedding-ada-002": 0.0001,
            "text-embedding-3-small": 0.00002,
            "text-embedding-3-large": 0.00013,
        }
        
        self.logger.info(f"Initialized OpenAI embeddings with model: {self.default_model}")
    
    async def embed_text(
        self,
        text: str,
        model: Optional[str] = None,
        **kwargs
    ) -> EmbeddingResponse:
        """Generate embedding for a single text."""
        model = model or self.default_model
        start_time = time.time()
        
        try:
            response = await self.client.embeddings.create(
                model=model,
                input=text,
                **kwargs
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Extract embedding and usage
            embedding_data = response.data[0]
            usage = response.usage.dict() if response.usage else {}
            
            # Calculate cost
            cost = self._calculate_cost(model, usage)
            
            # Log the request
            self.logger.debug(
                f"Generated embedding - model: {model}, "
                f"tokens: {usage.get('total_tokens', 0)}, "
                f"duration: {duration_ms:.2f}ms"
            )
            
            return EmbeddingResponse(
                embedding=embedding_data.embedding,
                model=model,
                usage=usage
            )
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(f"OpenAI embedding error after {duration_ms:.2f}ms: {e}")
            raise
    
    async def embed_texts(
        self,
        texts: List[str],
        model: Optional[str] = None,
        batch_size: int = 100,
        **kwargs
    ) -> List[EmbeddingResponse]:
        """Generate embeddings for multiple texts."""
        model = model or self.default_model
        
        if not texts:
            return []
        
        # Process in batches to avoid API limits
        all_responses = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_responses = await self._embed_batch(batch, model, **kwargs)
            all_responses.extend(batch_responses)
            
            # Small delay between batches to avoid rate limits
            if i + batch_size < len(texts):
                await asyncio.sleep(0.1)
        
        self.logger.info(f"Generated {len(all_responses)} embeddings in batches")
        return all_responses
    
    async def _embed_batch(
        self,
        texts: List[str],
        model: str,
        **kwargs
    ) -> List[EmbeddingResponse]:
        """Embed a batch of texts."""
        start_time = time.time()
        
        try:
            response = await self.client.embeddings.create(
                model=model,
                input=texts,
                **kwargs
            )
            
            duration_ms = (time.time() - start_time) * 1000
            usage = response.usage.dict() if response.usage else {}
            cost = self._calculate_cost(model, usage)
            
            # Log batch request
            self.logger.debug(
                f"Generated batch embeddings - model: {model}, "
                f"batch_size: {len(texts)}, "
                f"tokens: {usage.get('total_tokens', 0)}, "
                f"duration: {duration_ms:.2f}ms"
            )
            
            # Create response objects
            responses = []
            for i, embedding_data in enumerate(response.data):
                responses.append(EmbeddingResponse(
                    embedding=embedding_data.embedding,
                    model=model,
                    usage={
                        "total_tokens": usage.get('total_tokens', 0) // len(texts),
                        "prompt_tokens": usage.get('prompt_tokens', 0) // len(texts),
                    }
                ))
            
            return responses
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                f"OpenAI batch embedding error after {duration_ms:.2f}ms: {e}"
            )
            raise
    
    def get_embedding_dimension(self, model: Optional[str] = None) -> int:
        """Get embedding dimension for the model."""
        model = model or self.default_model
        return self.model_dimensions.get(model, 1536)
    
    async def validate_connection(self) -> bool:
        """Validate OpenAI embeddings API connection."""
        try:
            # Make a minimal API call to test connection
            await self.embed_text("test", model=self.default_model)
            self.logger.info("OpenAI embeddings connection validated successfully")
            return True
        
        except Exception as e:
            self.logger.error(f"OpenAI embeddings connection validation failed: {e}")
            return False
    
    def _calculate_cost(self, model: str, usage: dict) -> Optional[float]:
        """Calculate cost based on token usage."""
        if model not in self.token_pricing:
            return None
        
        total_tokens = usage.get("total_tokens", 0)
        cost_per_1k = self.token_pricing[model]
        
        return (total_tokens / 1000) * cost_per_1k
    
    def get_available_models(self) -> List[str]:
        """Get list of available embedding models."""
        return list(self.model_dimensions.keys())
    
    async def similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """Calculate cosine similarity between two embeddings."""
        import math
        
        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        
        # Calculate magnitudes
        magnitude1 = math.sqrt(sum(a * a for a in embedding1))
        magnitude2 = math.sqrt(sum(b * b for b in embedding2))
        
        # Calculate cosine similarity
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def truncate_text(self, text: str, model: Optional[str] = None) -> str:
        """Truncate text to fit model's token limit."""
        model = model or self.default_model
        
        # Approximate token limits for embedding models
        token_limits = {
            "text-embedding-ada-002": 8191,
            "text-embedding-3-small": 8191,
            "text-embedding-3-large": 8191,
        }
        
        max_tokens = token_limits.get(model, 8191)
        
        # Rough approximation: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        
        if len(text) <= max_chars:
            return text
        
        # Truncate and log warning
        truncated = text[:max_chars]
        self.logger.warning(
            f"Text truncated from {len(text)} to {len(truncated)} characters "
            f"for model {model}"
        )
        
        return truncated
