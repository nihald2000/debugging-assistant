import pytest
from unittest.mock import Mock, patch, AsyncMock
from agents.gemini_agent import GeminiAgent

@pytest.mark.unit
class TestGeminiAgent:
    
    @pytest.fixture
    def agent(self, mock_api_config):
        return GeminiAgent(api_key=mock_api_config.gemini_api_key)

    @pytest.mark.asyncio
    async def test_image_analysis(self, agent):
        """Test image analysis."""
        with patch.object(agent, '_generate_with_retry') as mock_generate, \
             patch.object(agent, '_preprocess_image') as mock_preprocess:
            
            # Mock preprocessing
            mock_preprocess.return_value = Mock()
            
            # Mock response
            mock_response = Mock()
            mock_response.text = '''
            {
                "detected_error": "TypeError: NoneType",
                "error_location": "line 42",
                "ui_context": "IDE editor",
                "suggested_focus_areas": ["app.py"],
                "confidence_score": 0.9
            }
            '''
            mock_generate.return_value = mock_response
            
            # Test
            result = await agent.analyze({
                "image": "fake_image_data",
                "type": "ide"
            })
            
            assert result["detected_error"] == "TypeError: NoneType"
            assert result["confidence_score"] == 0.9
            mock_generate.assert_called_once()
    
    def test_image_preprocessing(self, agent):
        """Test image preprocessing validates input."""
        from PIL import Image
        import io
        
        # Create test image
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        
        # Test preprocessing
        processed = agent._preprocess_image(img_bytes.getvalue())
        assert isinstance(processed, Image.Image)
