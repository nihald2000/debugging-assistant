"""
DebugGenie - AI-Powered Debugging Assistant
Main entry point for local and HuggingFace Spaces deployment
"""

import os
import sys
from ui.gradio_interface import create_interface
from loguru import logger

# Detect if running on HuggingFace Spaces
IS_SPACES = os.getenv("SPACE_ID") is not None

# Configure logging
if not IS_SPACES:
    logger.add("debuggenie.log", rotation="10 MB", level="INFO")

# Load HuggingFace Spaces secrets if available
if IS_SPACES:
    os.environ['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY', '')
    os.environ['GOOGLE_AI_API_KEY'] = os.getenv('GOOGLE_AI_API_KEY', '')
    os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', '')
    os.environ['ELEVENLABS_API_KEY'] = os.getenv('ELEVENLABS_API_KEY', '')
    os.environ['BLAXEL_API_KEY'] = os.getenv('BLAXEL_API_KEY', '')
    logger.info("🤗 Running on HuggingFace Spaces")
else:
    logger.info("💻 Running locally")

def main():
    """Launch the DebugGenie application."""
    logger.info("Starting DebugGenie...")
    
    demo = create_interface()
    
    if IS_SPACES:
        demo.queue(max_size=10, default_concurrency_limit=5)
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            show_error=True
        )
    else:
        demo.queue(max_size=20)
        demo.launch(
            server_name="0.0.0.0",
            server_port=7860,
            share=False,
            show_error=True
        )

if __name__ == "__main__":
    main()
