import pytest
import time
import asyncio
from unittest.mock import AsyncMock

@pytest.mark.slow
class TestPerformance:
    
    @pytest.mark.asyncio
    async def test_orchestrator_parallel_execution(self):
        """Test that agents run in parallel, not sequentially."""
        from core.orchestrator import DebugOrchestrator
        
        orchestrator = DebugOrchestrator()
        
        # Mock agents with delays
        async def slow_analyze(*args, **kwargs):
            await asyncio.sleep(1)  # 1 second delay
            return {"status": "success", "confidence_score": 0.8}
        
        orchestrator.gemini_agent.analyze = slow_analyze
        orchestrator.claude_agent.analyze = slow_analyze
        orchestrator.openai_agent.analyze = slow_analyze
        orchestrator.synthesizer.call_llm = AsyncMock(return_value='''
        {"root_cause": "Test", "solutions": [], "fix_instructions": "",
         "confidence_score": 0.5}
        ''')
        
        # Measure execution time
        start = time.time()
        await orchestrator.orchestrate_debug({"error_text": "test error"})
        duration = time.time() - start
        
        # If parallel: ~1 second, if sequential: ~3 seconds
        assert duration < 2.0, "Agents should run in parallel"
    
    @pytest.mark.asyncio
    async def test_cache_reduces_api_calls(self):
        """Test that caching reduces redundant API calls."""
        from agents.base_agent import BaseAgent
        
        class TestAgent(BaseAgent):
            def __init__(self):
                super().__init__("test_key", "test_model")
                self.call_count = 0
            
            async def _call_provider(self, prompt: str) -> str:
                self.call_count += 1
                return "test response"
            
            async def _stream_provider(self, prompt: str):
                yield "test"
            
            async def analyze(self, context):
                return {}
            
            def format_prompt(self, context):
                return ""
        
        agent = TestAgent()
        
        # First call
        response1 = await agent.call_llm("test prompt")
        assert agent.call_count == 1
        
        # Second call with same prompt (should use cache)
        response2 = await agent.call_llm("test prompt")
        assert agent.call_count == 1  # No additional call
        assert response1 == response2
    
    def test_rate_limiter_performance(self):
        """Test rate limiter doesn't significantly slow requests."""
        from mcp_servers.filesystem_mcp import RateLimiter
        
        limiter = RateLimiter(max_requests=1000, window_seconds=60)
        
        # Time 100 checks
        start = time.time()
        for i in range(100):
            limiter.check_rate_limit(f"client_{i}")
        duration = time.time() - start
        
        # Should be very fast (< 100ms for 100 checks)
        assert duration < 0.1
