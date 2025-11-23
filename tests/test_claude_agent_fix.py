import asyncio
import sys
import os
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.claude_agent import ClaudeAgent

async def test_claude_agent():
    print("Testing ClaudeAgent fix...")
    
    # Mock dependencies to avoid actual API calls
    with patch("agents.claude_agent.CodeAgent") as MockCodeAgent, \
         patch("agents.claude_agent.LiteLLMModel") as MockLiteLLMModel:
        
        # Setup mock agent
        mock_agent_instance = MockCodeAgent.return_value
        mock_agent_instance.run.return_value = "Mocked agent response"
        
        # Initialize ClaudeAgent
        agent = ClaudeAgent(api_key="dummy", model="dummy-model")
        
        # Test _call_provider
        print("\n1. Testing _call_provider...")
        response = await agent._call_provider("Test prompt")
        print(f"Response: {response}")
        assert response == "Mocked agent response"
        mock_agent_instance.run.assert_called_once()
        print("PASS: _call_provider called agent.run()")

        # Test _stream_provider
        print("\n2. Testing _stream_provider...")
        streamed_response = ""
        async for chunk in agent._stream_provider("Test prompt"):
            streamed_response += chunk
            print(f"Chunk: {chunk}", end="|")
        print(f"\nFull streamed response: {streamed_response}")
        assert streamed_response == "Mocked agent response"
        print("PASS: _stream_provider streamed correctly")

if __name__ == "__main__":
    asyncio.run(test_claude_agent())
