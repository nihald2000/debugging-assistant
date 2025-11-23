import pytest
from unittest.mock import patch, Mock, AsyncMock

@pytest.mark.integration
@pytest.mark.slow
class TestEndToEnd:
    
    @pytest.mark.asyncio
    async def test_full_debugging_flow(self, sample_error, mock_api_config):
        """Test complete debugging flow from error to solution."""
        
        # Mock all external dependencies
        with patch('agents.gemini_agent.genai'), \
             patch('agents.claude_agent.CodeAgent'), \
             patch('agents.openai_agent.Swarm'):
            
            from core.orchestrator import DebugOrchestrator
            orchestrator = DebugOrchestrator()
            
            # Mock agent responses
            orchestrator.gemini_agent.analyze = AsyncMock(return_value={
                "detected_error": "JSONDecodeError",
                "error_location": "app.py:42",
                "confidence_score": 0.9
            })
            
            orchestrator.claude_agent.analyze = AsyncMock(return_value={
                "root_cause_hypothesis": "Invalid JSON string",
                "affected_files": ["app.py"],
                "confidence_score": 0.85
            })
            
            orchestrator.openai_agent.analyze = AsyncMock(return_value={
                "swarm_analysis": "Add JSON validation",
                "status": "success"
            })
            
            orchestrator.synthesizer.call_llm = AsyncMock(return_value='''
            {
                "root_cause": "The input data is not valid JSON",
                "solutions": [
                    {
                        "title": "Add input validation",
                        "description": "Validate data before json.loads()",
                        "probability": 0.9
                    },
                    {
                        "title": "Use try-except",
                        "description": "Catch JSONDecodeError",
                        "probability": 0.7
                    }
                ],
                "fix_instructions": "Add: try/except around json.loads()",
                "confidence_score": 0.88
            }
            ''')
            
            # Execute full flow
            result = await orchestrator.orchestrate_debug({
                "error_text": sample_error
            })
            
            # Verify results
            assert "JSON" in result.root_cause
            assert len(result.solutions) == 2
            assert result.solutions[0]["title"] == "Add input validation"
            assert result.confidence_score >= 0.8
            assert result.execution_time > 0
    
    @pytest.mark.asyncio
    async def test_gradio_interface_analyze(self, sample_error):
        """Test Gradio interface analysis handler."""
        
        from ui.gradio_interface import DebugGenieUI
        
        with patch('ui.gradio_interface.DebugOrchestrator') as MockOrch:
            # Setup mocks
            mock_orchestrator = MockOrch.return_value
            mock_result = Mock()
            mock_result.root_cause = "Test error"
            mock_result.solutions = [
                {"title": "Fix 1", "description": "Do this", "probability": 0.9}
            ]
            mock_result.fix_instructions = "Step 1, Step 2"
            mock_result.confidence_score = 0.85
            mock_result.execution_time = 2.5
            mock_result.agent_metrics = {}
            
            mock_orchestrator.orchestrate_debug = AsyncMock(
                return_value=mock_result
            )
            
            # Test UI
            ui = DebugGenieUI()
            ui.orchestrator = mock_orchestrator
            
            # Mock progress
            progress = Mock()
            progress.return_value = None
            
            result = await ui.handle_analyze(
                error_text=sample_error,
                screenshot=None,
                codebase_files=None,
                progress=progress
            )
            
            # Verify UI response format
            chat_history, solutions_html, viz_html, voice, analysis, status = result
            
            assert len(chat_history) == 2  # User + Assistant
            assert "Fix 1" in solutions_html
            assert "✅" in status
