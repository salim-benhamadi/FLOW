from pydantic_settings import BaseSettings
from typing import List, Dict
from functools import lru_cache
import os
from pydantic import validator

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "Distribution Classifier"
    DEBUG: bool = False
    VERSION: str = "1.0.0"
    
    # API settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    API_PREFIX: str = "/api/v1"
    
    # Model settings
    MODEL_PATH: str = "./src/backend/models/lightgbm_model.txt"
    REFERENCE_DATA_PATH: str = "./data/reference_data.eff"
    CONFIDENCE_THRESHOLD: float = 0.95
    MODEL_VERSION: str = "1.0.0"
    
    # Database settings
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "postgres")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "root")
    
    # Database pool settings
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    
    # Default model settings
    DEFAULT_MODEL_SETTINGS: Dict = {
        "confidence_threshold": 0.95,
        "critical_issue_weight": 10.0,
        "high_priority_weight": 7.0,
        "normal_priority_weight": 3.0,
        "auto_retrain": True,
        "retraining_schedule": "weekly"
    }
    
    # Feedback settings
    SEVERITY_LEVELS: List[str] = ["HIGH", "CRITICAL", "MEDIUM"]
    FEEDBACK_STATUSES: List[str] = ["PENDING", "IGNORED", "RESOLVED"]
    TRAINING_REASONS: List[str] = ["FEEDBACK", "NEW_DATA", "ADMIN_INITIATIVE"]
    TRAINING_STATUSES: List[str] = ["SUCCESS", "FAILING"]
    
    @property
    def DATABASE_URL(self) -> str:
        """Get SQLAlchemy database URL"""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def DB_POOL_SETTINGS(self) -> Dict:
        """Get database pool settings"""
        return {
            "pool_size": self.DB_POOL_SIZE,
            "max_overflow": self.DB_MAX_OVERFLOW,
            "pool_timeout": self.DB_POOL_TIMEOUT,
            "pool_recycle": self.DB_POOL_RECYCLE
        }

    @validator("CONFIDENCE_THRESHOLD")
    def validate_confidence_threshold(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("Confidence threshold must be between 0 and 1")
        return v

    @validator("DEFAULT_MODEL_SETTINGS")
    def validate_model_settings(cls, v):
        required_keys = [
            "confidence_threshold",
            "critical_issue_weight",
            "high_priority_weight",
            "normal_priority_weight",
            "auto_retrain",
            "retraining_schedule"
        ]
        for key in required_keys:
            if key not in v:
                raise ValueError(f"Missing required model setting: {key}")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Additional utility functions
def get_db_url() -> str:
    """Get database URL with current settings"""
    settings = get_settings()
    return settings.DATABASE_URL

def get_db_pool_settings() -> Dict:
    """Get database pool settings with current settings"""
    settings = get_settings()
    return settings.DB_POOL_SETTINGS