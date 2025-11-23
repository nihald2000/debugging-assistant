import modal
import sys
import os

# Add current directory to path so we can import modules
sys.path.append(os.path.dirname(__file__))

from config.settings import settings

app = modal.App("debuggenie-app")

# Define image with dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "portaudio19-dev")
    .pip_install_from_requirements("requirements.txt")
    .env({"DEBUGGENIE_WORKSPACE": "/data"})
)

# Persistent volume for workspace
volume = modal.Volume.from_name("debuggenie-data", create_if_missing=True)

@app.function(
    image=image,
    secrets=[modal.Secret.from_name("debuggenie-secrets")],
    volumes={"/data": volume},
    gpu="T4",  # Use T4 GPU for faster inference if needed
    timeout=600
)
@modal.fastapi_endpoint(method="POST")
def analyze_error(error_info: dict):
    """
    Analyze an error using the DebugOrchestrator.
    Expects a JSON body with "error_text" and optional "context".
    """
    from core.orchestrator import DebugOrchestrator
    import asyncio
    
    # Initialize orchestrator with keys from environment (injected by secrets)
    # Note: settings.py automatically reads from os.environ
    orch = DebugOrchestrator()
    
    # Run analysis
    result = asyncio.run(orch.orchestrate_debug(error_info))
    
    # Convert result to dict for JSON response
    return result.model_dump()
