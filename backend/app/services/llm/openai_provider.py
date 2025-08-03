"""
OpenAI LLM provider implementation.

This module provides OpenAI GPT integration following the LLMProvider interface.
"""

import time
from typing import Any, Dict, List, Optional, Union, AsyncGenerator

import openai
import tiktoken
from openai import AsyncOpenAI

from ...core.config import settings
from ...core.logging import get_logger, log_llm_request
from ..base import LLMProvider, LLMResponse


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider implementation."""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """Initialize OpenAI provider."""
        self.api_key = api_key or settings.openai.api_key
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.logger = get_logger(self.__class__.__name__)
        
        # Model configuration
        self.default_model = settings.openai.model
        self.default_max_tokens = settings.openai.max_tokens
        self.default_temperature = settings.openai.temperature
        
        # Token pricing (approximate, in USD per 1K tokens)
        self.token_pricing = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},
            "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
        }
        
        self.logger.info(f"Initialized OpenAI provider with model: {self.default_model}")
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[LLMResponse, AsyncGenerator[str, None]]:
        """Generate response from OpenAI GPT."""
        model = model or self.default_model
        max_tokens = max_tokens or self.default_max_tokens
        temperature = temperature or self.default_temperature
        
        start_time = time.time()
        
        try:
            # Prepare request parameters
            request_params = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                **kwargs
            }
            
            if stream:
                return self._stream_response(request_params, start_time)
            
            # Make API call
            response = await self.client.chat.completions.create(**request_params)
            
            # Calculate duration and cost
            duration_ms = (time.time() - start_time) * 1000
            usage = response.usage.dict() if response.usage else {}
            cost = self._calculate_cost(model, usage)
            
            # Log the request
            log_llm_request(
                self.logger,
                provider="openai",
                model=model,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                duration_ms=duration_ms,
                cost=cost
            )
            
            # Create response object
            llm_response = LLMResponse(
                content=response.choices[0].message.content,
                model=model,
                usage=usage,
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "cost_usd": cost,
                    "duration_ms": duration_ms,
                }
            )
            
            return llm_response
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(f"OpenAI API error after {duration_ms:.2f}ms: {e}")
            raise
    
    async def _stream_response(
        self,
        request_params: Dict[str, Any],
        start_time: float
    ) -> AsyncGenerator[str, None]:
        """Stream response from OpenAI."""
        request_params["stream"] = True
        
        try:
            stream = await self.client.chat.completions.create(**request_params)
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
            
            duration_ms = (time.time() - start_time) * 1000
            self.logger.info(f"Streamed OpenAI response in {duration_ms:.2f}ms")
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(f"OpenAI streaming error after {duration_ms:.2f}ms: {e}")
            raise
    
    async def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """Count tokens using tiktoken."""
        model = model or self.default_model
        
        try:
            # Get encoding for the model
            if model.startswith("gpt-4"):
                encoding_name = "cl100k_base"
            elif model.startswith("gpt-3.5"):
                encoding_name = "cl100k_base"
            else:
                encoding_name = "cl100k_base"  # Default
            
            encoding = tiktoken.get_encoding(encoding_name)
            tokens = encoding.encode(text)
            
            return len(tokens)
        
        except Exception as e:
            self.logger.warning(f"Token counting error: {e}")
            # Fallback to approximate count
            return len(text.split()) * 1.3  # Rough approximation
    
    def get_available_models(self) -> List[str]:
        """Get list of available OpenAI models."""
        return [
            "gpt-4",
            "gpt-4-turbo-preview",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
        ]
    
    async def validate_connection(self) -> bool:
        """Validate OpenAI API connection."""
        try:
            # Make a minimal API call to test connection
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=1
            )
            
            self.logger.info("OpenAI connection validated successfully")
            return True
        
        except Exception as e:
            self.logger.error(f"OpenAI connection validation failed: {e}")
            return False
    
    def _calculate_cost(self, model: str, usage: Dict[str, int]) -> Optional[float]:
        """Calculate cost based on token usage."""
        if model not in self.token_pricing:
            return None
        
        pricing = self.token_pricing[model]
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        cost = (
            (prompt_tokens / 1000) * pricing["input"] +
            (completion_tokens / 1000) * pricing["output"]
        )
        
        return cost
    
    async def create_embedding(
        self,
        text: str,
        model: Optional[str] = None
    ) -> List[float]:
        """Create embedding using OpenAI embeddings API."""
        model = model or settings.openai.embedding_model
        
        try:
            response = await self.client.embeddings.create(
                model=model,
                input=text
            )
            
            return response.data[0].embedding
        
        except Exception as e:
            self.logger.error(f"OpenAI embedding error: {e}")
            raise
    
    def get_context_length(self, model: Optional[str] = None) -> int:
        """Get maximum context length for model."""
        model = model or self.default_model
        
        context_lengths = {
            "gpt-4": 8192,
            "gpt-4-32k": 32768,
            "gpt-4-turbo-preview": 128000,
            "gpt-3.5-turbo": 4096,
            "gpt-3.5-turbo-16k": 16384,
        }
        
        return context_lengths.get(model, 4096)
    
    async def moderate_content(self, text: str) -> Dict[str, Any]:
        """Use OpenAI moderation API to check content."""
        try:
            response = await self.client.moderations.create(input=text)
            
            result = response.results[0]
            return {
                "flagged": result.flagged,
                "categories": result.categories.dict(),
                "category_scores": result.category_scores.dict(),
            }
        
        except Exception as e:
            self.logger.error(f"OpenAI moderation error: {e}")
            return {"flagged": False, "categories": {}, "category_scores": {}}
