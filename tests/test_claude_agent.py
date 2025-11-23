import pytest
from unittest.mock import Mock, patch, AsyncMock
from agents.claude_agent import ClaudeAgent

@pytest.mark.unit
class TestClaudeAgent:
    
    @pytest.fixture
    def agent(self, mock_api_config):
        return ClaudeAgent(api_key=mock_api_config.anthropic_api_key)
    
    @pytest.mark.asyncio
    async def test_call_provider_wraps_smolagents(self, agent):
        """Test _call_provider properly wraps smolagents."""
        with patch.object(agent.agent, 'run', return_value="Test response"):
            result = await agent._call_provider("Test prompt")
            assert result == "Test response"
    
    @pytest.mark.asyncio
    async def test_stream_provider_chunks_response(self, agent):
        """Test _stream_provider yields chunks."""
        with patch.object(agent.agent, 'run', return_value="Word1 Word2 Word3"):
            chunks = []
            async for chunk in agent._stream_provider("Test"):
                chunks.append(chunk)
            
            assert len(chunks) > 0
            assert "".join(chunks) == "Word1 Word2 Word3"
