from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Groq API Configuration (NEW - super fast!)
    groq_api_key: str = ""
    
    # Speechmatics Configuration
    speechmatics_api_key: str = ""
    
    # MURF.ai Configuration
    murf_api_key: str = ""
    murf_voice_id: str = "en-US-JennyNeural"
    
    # Chroma DB Configuration
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    
    # Application Configuration
    upload_dir: str = "./uploads"
    chroma_persist_dir: str = "./chroma_db"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env
    
    @property
    def cors_origins(self) -> List[str]:
        """Get CORS origins."""
        return [
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:5175",
            "http://localhost:3000"
        ]

settings = Settings()

# Create necessary directories
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.chroma_persist_dir, exist_ok=True)
