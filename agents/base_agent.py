from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, AsyncGenerator, List
import time
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from cachetools import TTLCache
from loguru import logger

class BaseAgent(ABC):
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        # Cache: 100 items, 1 hour TTL
        self.cache = TTLCache(maxsize=100, ttl=3600)
        # Metrics
        self.metrics = {
            "total_tokens": 0,
            "total_latency": 0.0,
            "api_calls": 0,
            "errors": 0
        }
        # Rate limiting (simple token bucket or request spacing)
        self.last_request_time = 0
        self.min_request_interval = 0.5 # seconds

    @abstractmethod
    async def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze error and return findings."""
        pass
    
    @abstractmethod
    def format_prompt(self, context: Dict[str, Any]) -> str:
        """Format the prompt for this agent's LLM."""
        pass

    @abstractmethod
    async def _call_provider(self, prompt: str) -> str:
        """
        Implement the actual API call to the provider.
        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    async def _stream_provider(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Implement streaming API call to the provider.
        Must be implemented by subclasses.
        """
        pass

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count (heuristic: 1 token ~= 4 chars).
        Subclasses can override with more accurate logic.
        """
        return len(text) // 4

    async def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception) # Broad retry for now, subclasses can refine
    )
    async def call_llm(self, prompt: str) -> str:
        """
        Make API call to LLM with retries, caching, and metrics.
        """
        # Check cache
        if prompt in self.cache:
            logger.info(f"Cache hit for prompt: {prompt[:50]}...")
            return self.cache[prompt]

        await self._wait_for_rate_limit()
        
        start_time = time.time()
        try:
            logger.info(f"Calling LLM ({self.model}) with prompt length: {len(prompt)}")
            
            response = await self._call_provider(prompt)
            
            # Update metrics
            latency = time.time() - start_time
            self.metrics["total_latency"] += latency
            self.metrics["api_calls"] += 1
            
            # Estimate tokens (input + output)
            input_tokens = self._estimate_tokens(prompt)
            output_tokens = self._estimate_tokens(response)
            self.metrics["total_tokens"] += (input_tokens + output_tokens)
            
            logger.info(f"LLM call successful. Latency: {latency:.2f}s, Tokens: {input_tokens+output_tokens}")
            
            # Cache result
            self.cache[prompt] = response
            return response
            
        except Exception as e:
            self.metrics["errors"] += 1
            logger.error(f"LLM call failed: {e}")
            raise

    async def stream_llm(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Stream API call to LLM with metrics.
        Note: Streaming responses are NOT cached.
        """
        await self._wait_for_rate_limit()
        
        start_time = time.time()
        try:
            logger.info(f"Streaming LLM ({self.model}) with prompt length: {len(prompt)}")
            
            full_response = []
            async for chunk in self._stream_provider(prompt):
                full_response.append(chunk)
                yield chunk
            
            # Update metrics after stream completes
            latency = time.time() - start_time
            response_text = "".join(full_response)
            
            self.metrics["total_latency"] += latency
            self.metrics["api_calls"] += 1
            
            input_tokens = self._estimate_tokens(prompt)
            output_tokens = self._estimate_tokens(response_text)
            self.metrics["total_tokens"] += (input_tokens + output_tokens)
            
            logger.info(f"LLM stream successful. Latency: {latency:.2f}s")
            
        except Exception as e:
            self.metrics["errors"] += 1
            logger.error(f"LLM stream failed: {e}")
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Return current metrics."""
        return self.metrics
