from pydantic_settings import BaseSettings
from typing import List, Dict
from functools import lru_cache
import os
from pathlib import Path

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
    
    # Model settings - Container vs local paths
    MODEL_PATH: str = os.getenv("MODEL_PATH", self._get_default_model_path())
    REFERENCE_DATA_PATH: str = os.getenv("REFERENCE_DATA_PATH", self._get_default_reference_path())
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.95"))
    MODEL_VERSION: str = "1.0.0"
    
    # Database settings
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "postgres")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    
    # Cloud-specific settings
    DATABASE_SSL_MODE: str = os.getenv("DATABASE_SSL_MODE", "prefer")
    
    @staticmethod
    def _get_default_model_path() -> str:
        """Get default model path based on environment"""
        # Check if running in OpenShift container
        if os.path.exists("/opt/app-root/src"):
            return "/opt/app-root/src/backend/models/lightgbm_model.txt"
        else:
            # Local development
            project_root = Path(__file__).resolve().parent.parent.parent
            return str(project_root / "backend" / "models" / "lightgbm_model.txt")
    
    @staticmethod
    def _get_default_reference_path() -> str:
        """Get default reference data path based on environment"""
        # Check if running in OpenShift container
        if os.path.exists("/opt/app-root/src"):
            return "/opt/app-root/src/backend/data/reference_data.eff"
        else:
            # Local development
            project_root = Path(__file__).resolve().parent.parent.parent
            return str(project_root / "backend" / "data" / "reference_data.eff")
    
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