# frontend/config/api_config.py
import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

class APIConfig:
    """Centralized API configuration for frontend using .env file"""
    
    def __init__(self):
        self._base_url = None
        self._timeout = None
        self._verify_ssl = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from .env file and environment variables"""
        # Load .env file from frontend directory
        env_file = Path(__file__).parent.parent / '.env'
        load_dotenv(env_file)
        
        # Load configuration values
        self._base_url = os.getenv('VAMOS_API_URL', 'http://localhost:8000')
        self._timeout = float(os.getenv('API_TIMEOUT', '30.0'))
        self._verify_ssl = os.getenv('API_VERIFY_SSL', 'true').lower() == 'true'
        
        # Clean up base URL
        self._base_url = self._base_url.rstrip('/')
    
    @property
    def base_url(self) -> str:
        """Get the API base URL"""
        return self._base_url
    
    @property
    def timeout(self) -> float:
        """Get the API timeout"""
        return self._timeout
    
    @property
    def verify_ssl(self) -> bool:
        """Get SSL verification setting"""
        return self._verify_ssl
    
    @property
    def is_production(self) -> bool:
        """Check if using production endpoint"""
        return 'localhost' not in self._base_url and '127.0.0.1' not in self._base_url
    
    @property
    def is_local(self) -> bool:
        """Check if using local development endpoint"""
        return not self.is_production
    
    def get_headers(self) -> dict:
        """Get default headers for API requests"""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Add additional headers for production if needed
        if self.is_production:
            headers["User-Agent"] = "VAMOS-Desktop-Client/1.0"
        
        return headers


# Global configuration instance
api_config = APIConfig()

def get_api_base_url() -> str:
    """Get the configured API base URL"""
    return api_config.base_url

def get_api_timeout() -> float:
    """Get the configured API timeout"""
    return api_config.timeout

def get_api_verify_ssl() -> bool:
    """Get SSL verification setting"""
    return api_config.verify_ssl

def get_api_headers() -> dict:
    """Get default API headers"""
    return api_config.get_headers()

def is_production() -> bool:
    """Check if running in production mode"""
    return api_config.is_production