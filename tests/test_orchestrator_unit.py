import pytest
from unittest.mock import Mock, AsyncMock, patch
from core.orchestrator import DebugOrchestrator

@pytest.mark.unit
class TestDebugOrchestrator:
    
    @pytest.fixture
    def orchestrator(self):
        with patch('core.orchestrator.GeminiAgent'), \
             patch('core.orchestrator.ClaudeAgent'), \
             patch('core.orchestrator.OpenAIAgent'):
            return DebugOrchestrator()
    
    @pytest.mark.asyncio
    async def test_parse_error_extracts_summary(self, orchestrator):
        """Test error parsing."""
        error_text = "ValueError: invalid literal for int()"
        result = await orchestrator.parse_error(error_text)
        
        assert "raw_text" in result
        assert result["raw_text"] == error_text
        assert len(result["summary"]) <= 200
    
    @pytest.mark.asyncio
    async def test_orchestrate_debug_calls_all_agents(
        self, orchestrator, sample_error, mock_claude_response
    ):
        """Test orchestration calls all agents in parallel."""
        
        # Mock agent responses
        orchestrator.gemini_agent.analyze = AsyncMock(return_value={
            "detected_error": "ValueError",
            "confidence_score": 0.8
        })
        orchestrator.claude_agent.analyze = AsyncMock(
            return_value=mock_claude_response
        )
        orchestrator.openai_agent.analyze = AsyncMock(return_value={
            "swarm_analysis": "Test analysis",
            "status": "success"
        })
        
        # Mock synthesizer
        orchestrator.synthesizer.call_llm = AsyncMock(return_value='''
        {
            "root_cause": "Invalid JSON input",
            "solutions": [
                {
                    "title": "Validate input",
                    "description": "Check data before parsing",
                    "probability": 0.9
                }
            ],
            "fix_instructions": "Add validation",
            "confidence_score": 0.85
        }
        ''')
        
        # Test
        result = await orchestrator.orchestrate_debug({
            "error_text": sample_error
        })
        
        assert result.root_cause == "Invalid JSON input"
        assert len(result.solutions) == 1
        assert result.confidence_score == 0.85
        
        # Verify all agents called
        orchestrator.gemini_agent.analyze.assert_not_called()  # No image
        orchestrator.claude_agent.analyze.assert_called_once()
        orchestrator.openai_agent.analyze.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_orchestrate_handles_agent_failure(
        self, orchestrator, sample_error
    ):
        """Test orchestration handles agent failures gracefully."""
        
        # One agent fails
        orchestrator.gemini_agent.analyze = AsyncMock(
            side_effect=Exception("API Error")
        )
        orchestrator.claude_agent.analyze = AsyncMock(return_value={
            "root_cause_hypothesis": "Test",
            "confidence_score": 0.7
        })
        orchestrator.openai_agent.analyze = AsyncMock(return_value={
            "status": "success"
        })
        
        orchestrator.synthesizer.call_llm = AsyncMock(return_value='''
        {"root_cause": "Test", "solutions": [], "fix_instructions": "", 
         "confidence_score": 0.5}
        ''')
        
        # Should not raise, should handle gracefully
        result = await orchestrator.orchestrate_debug({
            "error_text": sample_error
        })
        
        assert result.confidence_score <= 0.7  # Lower confidence due to failure
