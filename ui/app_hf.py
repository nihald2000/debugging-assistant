import os
import gradio as gr
from ui.gradio_interface import create_interface
from ui.remote_client import RemoteBackend

# Get Modal API URL from environment variable
MODAL_API_URL = os.environ.get("MODAL_API_URL")

if not MODAL_API_URL:
    raise ValueError("MODAL_API_URL environment variable is not set. Please configure it in Hugging Face Space secrets.")

# Initialize remote backend
backend = RemoteBackend(api_url=MODAL_API_URL)

# Create interface
demo = create_interface(backend)

if __name__ == "__main__":
    demo.launch()
