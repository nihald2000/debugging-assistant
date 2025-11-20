from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Centralized configuration for all API keys and IDs.
    Used for deployment to Modal, HuggingFace Spaces, and local development.
    """
    
    # AI Model API Keys
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GOOGLE_AI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""  # For Gemini Live API
    
    # Voice/Audio APIs
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_AGENT_ID: str = ""
    
    # External Services
    GITHUB_TOKEN: str = ""
    
    # Modal Configuration
    MODAL_TOKEN_ID: Optional[str] = None
    MODAL_TOKEN_SECRET: Optional[str] = None
    
    # HuggingFace
    HF_TOKEN: Optional[str] = None
    
    # Application Settings
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'
    )


# Singleton instance
settings = Settings()
