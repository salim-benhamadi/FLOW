from pydantic_settings import BaseSettings
from typing import List, Dict
from functools import lru_cache
import os
from pathlib import Path

# Get the project root directory (assuming config.py is in backend/core/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "VAMOS Distribution Classifier"
    DEBUG: bool = False
    VERSION: str = "1.0.0"
    
    # API settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: List[str] = ["*"]  
    API_PREFIX: str = "/api/v1"
    
    # Model settings - Use absolute paths resolved from project root
    MODEL_PATH: str = os.getenv("MODEL_PATH", str(PROJECT_ROOT / "backend" / "models" / "lightgbm_model.txt"))
    REFERENCE_DATA_PATH: str = os.getenv("REFERENCE_DATA_PATH", str(PROJECT_ROOT / "backend" / "data" / "reference_data.eff"))
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.95"))
    MODEL_VERSION: str = "1.0.0"
    
    # Database settings - will be overridden by environment variables
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "vamos-db")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "root")
    
    # Cloud-specific settings
    DATABASE_SSL_MODE: str = os.getenv("DATABASE_SSL_MODE", "prefer")
    
    @property
    def DATABASE_URL(self) -> str:
        """Get SQLAlchemy database URL"""
        ssl_param = f"?sslmode={self.DATABASE_SSL_MODE}" if self.DATABASE_SSL_MODE != "disable" else ""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}{ssl_param}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings():
    return Settings()