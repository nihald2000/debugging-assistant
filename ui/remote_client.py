import requests
import json
from typing import Dict, Any
from core.models import DebugResult
from ui.backend import DebugBackend
from loguru import logger

class RemoteBackend(DebugBackend):
    def __init__(self, api_url: str, token: str = None):
        self.api_url = api_url
        self.token = token

    async def analyze(self, context: Dict[str, Any]) -> DebugResult:
        """
        Call the remote Modal endpoint.
        """
        try:
            # Prepare payload
            # The Modal endpoint expects a dict with "error_text" and optional "context"
            # Our context already has 'error_text', 'image', 'code_context'
            # We might need to adapt if the endpoint signature is strict, 
            # but modal_app.py takes `error_info: dict`.
            
            # Note: Image handling might need base64 encoding if not already done.
            # In gradio_interface.py, 'image' is passed as PIL image or None.
            # We need to serialize it if it's a PIL image.
            
            payload = context.copy()
            if payload.get('image'):
                # If it's a PIL image, convert to base64
                import base64
                from io import BytesIO
                
                img = payload['image']
                if not isinstance(img, str):
                    buffered = BytesIO()
                    img.save(buffered, format="PNG")
                    img_str = base64.b64encode(buffered.getvalue()).decode()
                    payload['image'] = img_str
            
            headers = {"Content-Type": "application/json"}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            logger.info(f"Sending request to {self.api_url}")
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=600)
            response.raise_for_status()
            
            data = response.json()
            return DebugResult(**data)
            
        except Exception as e:
            logger.error(f"Remote analysis failed: {e}")
            raise e
