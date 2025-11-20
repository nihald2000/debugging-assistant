import os
import base64
import io
import json
from typing import Any, Dict, List, Optional, AsyncGenerator, Union
from PIL import Image
import google.generativeai as genai
from pydantic import BaseModel, Field
from .base_agent import BaseAgent
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

class VisualAnalysis(BaseModel):
    detected_error: str = Field(description="The specific error message or condition detected")
    error_location: str = Field(description="File path and line number if visible, or UI location")
    ui_context: str = Field(description="Description of the visible UI state")
    suggested_focus_areas: List[str] = Field(description="List of files or components to check")
    confidence_score: float = Field(description="Confidence score between 0.0 and 1.0")
    diagram_url: Optional[str] = Field(description="URL or path to generated debug diagram", default=None)

class GeminiAgent(BaseAgent):
    def __init__(self, api_key: str, model: str = "gemini-3.0-pro-exp-001"):
        super().__init__(api_key, model)
        genai.configure(api_key=api_key)
        
        # Configure Thinking Mode and Native Tools
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.2,
            response_mime_type="application/json",
            # Enable Flash Thinking for complex reasoning
            # Note: Exact API syntax for thinking mode may vary by SDK version
            thinking_config={"include_thoughts": True} 
        )
        
        # Initialize model with Google Search and Code Execution tools
        self.model_instance = genai.GenerativeModel(
            model_name=model,
            generation_config=self.generation_config,
            tools=[
                # Native Google Search integration
                {"google_search": {}},
                # Native Code Execution for testing fixes
                {"code_execution": {}}
            ]
        )

    def format_prompt(self, context: Dict[str, Any]) -> str:
        """Format simple text prompt from context."""
        return context.get("prompt", "")

    async def _call_provider(self, prompt: str) -> str:
        """Text-only generation."""
        response = await self.model_instance.generate_content_async(prompt)
        return response.text

    async def _stream_provider(self, prompt: str) -> AsyncGenerator[str, None]:
        """Text-only streaming."""
        response = await self.model_instance.generate_content_async(prompt, stream=True)
        async for chunk in response:
            yield chunk.text

    def _preprocess_image(self, image_data: Any) -> Image.Image:
        """Load, resize and validate image."""
        try:
            if isinstance(image_data, str):
                if os.path.exists(image_data):
                    img = Image.open(image_data)
                else:
                    if "base64," in image_data:
                        image_data = image_data.split("base64,")[1]
                    img = Image.open(io.BytesIO(base64.b64decode(image_data)))
            elif isinstance(image_data, bytes):
                img = Image.open(io.BytesIO(image_data))
            elif isinstance(image_data, Image.Image):
                img = image_data
            else:
                raise ValueError(f"Unsupported image type: {type(image_data)}")

            max_dim = 2048
            if img.width > max_dim or img.height > max_dim:
                img.thumbnail((max_dim, max_dim))
            
            return img
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _generate_with_retry(self, inputs: List[Any]) -> Any:
        """Internal helper to call Gemini with retry logic."""
        return await self.model_instance.generate_content_async(inputs)

    async def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze context using Gemini 3.0 Pro capabilities.
        Supports text, images, and native tool calling.
        """
        try:
            image_input = context.get("image")
            if not image_input:
                raise ValueError("No image provided in context")

            img = self._preprocess_image(image_input)
            context_type = context.get("type", "general")
            additional_text = context.get("additional_text", "")

            # Specialized prompts
            prompts = {
                "console": "Analyze this browser console screenshot for errors and stack traces.",
                "ide": "Analyze this IDE screenshot for code errors and context.",
                "terminal": "Analyze this terminal output for command failures.",
                "general": "Analyze this screenshot for technical issues."
            }

            base_prompt = prompts.get(context_type, prompts["general"])
            
            full_prompt = f"""
                {base_prompt}
                
                Additional Context: {additional_text}
                
                Task:
                1. Analyze the image and context deeply using thinking mode.
                2. Use Google Search to find info about specific error codes or libraries.
                3. Use Code Execution to:
                   - Verify assumptions about Python/JS syntax.
                   - Calculate values or simulate logic if relevant.
                4. Generate a visual diagram description if the error involves complex flow.
                
                Return a JSON object:
                {{
                    "detected_error": "string",
                    "error_location": "string",
                    "ui_context": "string",
                    "suggested_focus_areas": ["string"],
                    "confidence_score": float,
                    "diagram_description": "string (optional description for diagram generation)"
                }}
            """

            logger.info(f"Sending request to Gemini ({self.model}) - Type: {context_type}")
            
            # Call Gemini with image and prompt
            response = await self._generate_with_retry([full_prompt, img])
            
            # Handle Multimodal Output (Text + Potential Images/Search Results)
            response_text = response.text
            
            # Check for search grounding metadata (if available in response)
            # grounding_metadata = response.candidates[0].grounding_metadata
            
            # Clean json
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            data = json.loads(response_text)
            
            # Handle Diagram Generation (Native Image Output simulation)
            # If the model generated an image part, we would process it here.
            # Since standard API returns text/parts, we simulate the "Native Image Output" 
            # by checking if we requested it or if the model supports returning image parts.
            # For this implementation, we'll assume the user wants us to handle the "diagram_description"
            # and potentially generate it in a real scenario, or if the model returned an image part.
            
            # Placeholder for native image extraction if supported by 3.0 exp
            # images = [part for part in response.parts if part.mime_type.startswith('image/')]
            
            analysis = VisualAnalysis(**data)
            logger.info(f"Gemini analysis successful. Confidence: {analysis.confidence_score}")
            
            return analysis.model_dump()

        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")
            return {
                "detected_error": f"Analysis failed: {str(e)}",
                "error_location": "unknown",
                "ui_context": "unknown",
                "suggested_focus_areas": [],
                "confidence_score": 0.0
            }
