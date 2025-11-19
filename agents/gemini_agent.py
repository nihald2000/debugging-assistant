import os
import base64
import io
import json
from typing import Any, Dict, List, Optional, AsyncGenerator
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

class GeminiAgent(BaseAgent):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-001"):
        super().__init__(api_key, model)
        genai.configure(api_key=api_key)
        self.generation_config = genai.types.GenerationConfig(
            temperature=0.2,
            response_mime_type="application/json"
        )
        self.model_instance = genai.GenerativeModel(
            model_name=model,
            generation_config=self.generation_config
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
                # Check if it's a file path
                if os.path.exists(image_data):
                    img = Image.open(image_data)
                else:
                    # Try base64
                    # Remove header if present (e.g. "data:image/png;base64,")
                    if "base64," in image_data:
                        image_data = image_data.split("base64,")[1]
                    img = Image.open(io.BytesIO(base64.b64decode(image_data)))
            elif isinstance(image_data, bytes):
                img = Image.open(io.BytesIO(image_data))
            elif isinstance(image_data, Image.Image):
                img = image_data
            else:
                raise ValueError(f"Unsupported image type: {type(image_data)}")

            # Resize if too large to optimize latency/tokens
            max_dim = 2048
            if img.width > max_dim or img.height > max_dim:
                img.thumbnail((max_dim, max_dim))
            
            return img
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _generate_with_retry(self, inputs: List[Any]) -> str:
        """Internal helper to call Gemini with retry logic."""
        response = await self.model_instance.generate_content_async(inputs)
        return response.text

    async def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze context which must include an 'image' key.
        
        Args:
            context: Dict containing:
                - image: str (path/base64) or PIL.Image or bytes
                - type: str ('console', 'ide', 'terminal', 'general')
                - additional_text: str (optional)
        """
        try:
            image_input = context.get("image")
            if not image_input:
                raise ValueError("No image provided in context")

            img = self._preprocess_image(image_input)
            context_type = context.get("type", "general")
            additional_text = context.get("additional_text", "")

            # Specialized prompts based on context type
            prompts = {
                "console": """
                    Analyze this browser console screenshot.
                    1. Identify any error messages (red text), warnings, or failed network requests.
                    2. Extract specific error codes (e.g., 404, 500) and stack traces if visible.
                    3. Note the file names and line numbers in the stack trace.
                """,
                "ide": """
                    Analyze this IDE screenshot.
                    1. Identify the active file and line number (cursor position or highlighted line).
                    2. Read any visible error squiggles or hover tooltips.
                    3. Extract the code context around the error.
                """,
                "terminal": """
                    Analyze this terminal output.
                    1. Identify the command that was run.
                    2. Parse the error output, stack trace, and specific error message.
                    3. Ignore standard progress bars or unrelated logs.
                """,
                "general": """
                    Analyze this screenshot for any technical errors or bugs.
                    Identify error messages, UI anomalies, or code issues.
                """
            }

            base_prompt = prompts.get(context_type, prompts["general"])
            
            full_prompt = f"""
                {base_prompt}
                
                Additional Context: {additional_text}
                
                Return a JSON object matching this exact structure:
                {{
                    "detected_error": "string",
                    "error_location": "string",
                    "ui_context": "string",
                    "suggested_focus_areas": ["string (list of files/components)"],
                    "confidence_score": float (0.0 to 1.0)
                }}
            """

            logger.info(f"Sending image analysis request to Gemini ({self.model}) - Type: {context_type}")
            
            # Call Gemini with image and prompt
            response_text = await self._generate_with_retry([full_prompt, img])
            
            # Clean json block if needed
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            # Parse and validate
            data = json.loads(response_text)
            analysis = VisualAnalysis(**data)
            
            logger.info(f"Gemini analysis successful. Confidence: {analysis.confidence_score}")
            return analysis.model_dump()

        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")
            # Return a fallback error analysis structure
            return {
                "detected_error": f"Analysis failed: {str(e)}",
                "error_location": "unknown",
                "ui_context": "unknown",
                "suggested_focus_areas": [],
                "confidence_score": 0.0
            }
