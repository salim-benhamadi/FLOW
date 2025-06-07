from pydantic_settings import BaseSettings
from typing import List, Dict
from functools import lru_cache
import os

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
    
    # Model settings
    MODEL_PATH: str = "/app/backend/models/lightgbm_model.txt"
    REFERENCE_DATA_PATH: str = "/app/data/reference_data.eff"
    CONFIDENCE_THRESHOLD: float = 0.95
    MODEL_VERSION: str = "1.0.0"
    
    # Database settings - will be overridden by environment variables
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "postgres")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    
    # Cloud-specific settings
    DATABASE_SSL_MODE: str = os.getenv("DATABASE_SSL_MODE", "prefer")
    
    @property
    def DATABASE_URL(self) -> str:
        """Get SQLAlchemy database URL"""
        ssl_param = f"?sslmode={self.DATABASE_SSL_MODE}" if self.DATABASE_SSL_MODE != "disable" else ""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}{ssl_param}"

@lru_cache()
def get_settings():
    return Settings()