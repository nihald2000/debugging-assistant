from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, ValidationError
from dotenv import load_dotenv
import os
import sys

# Load environment variables from .env file
load_dotenv()

class APIConfig(BaseSettings):
    """
    Configuration for API keys using Pydantic for validation.
    """
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    anthropic_api_key: str = Field(..., description="API key for Anthropic Claude")
    google_ai_api_key: str = Field(..., description="API key for Google Gemini")
    openai_api_key: str = Field(..., description="API key for OpenAI GPT-4")
    elevenlabs_api_key: str = Field(..., description="API key for ElevenLabs TTS")
    blaxel_api_key: str = Field(..., description="API key for Blaxel Visualization")
    modal_token: str = Field(..., description="Token for Modal Labs deployment")
    hf_token: str = Field(..., description="Token for HuggingFace Spaces")

    @classmethod
    def load(cls):
        try:
            return cls()
        except ValidationError as e:
            print("❌ Configuration Error: Missing or invalid API keys.")
            for error in e.errors():
                field = error['loc'][0]
                print(f"   - {field}: {error['msg']}")
            sys.exit(1)

# Global instance
try:
    api_config = APIConfig.load()
except SystemExit:
    # Allow import without crashing if just checking structure, but in app run it will exit.
    # For now, let's just print a warning if imported in a context where env vars aren't set yet (like tests)
    # but the load() method explicitly calls sys.exit(1) on failure.
    pass
