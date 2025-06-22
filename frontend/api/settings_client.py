import requests
from typing import List, Dict, Optional
import logging
from api.api_config import get_api_base_url, get_api_headers, get_api_timeout, get_api_verify_ssl

logger = logging.getLogger(__name__)

class SettingsClient:
    def __init__(self):
        self.base_url = get_api_base_url()
        self.headers = get_api_headers()
        self.timeout = get_api_timeout()
        self.verify_ssl = get_api_verify_ssl()
        self.settings_endpoint = f"{self.base_url}/api/v1/settings"

    def get_available_products(self) -> List[str]:
        """Get list of available reference products from backend"""
        try:
            response = requests.get(
                f"{self.settings_endpoint}/available-products",
                headers=self.headers,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            data = response.json()
            return data.get('products', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching available products: {e}")
            return []

    def get_settings(self) -> Dict:
        """Get current settings from backend"""
        try:
            response = requests.get(
                f"{self.settings_endpoint}/settings",
                headers=self.headers,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching settings: {e}")
            return {"sensitivity": 0.5, "selected_products": []}

    def update_settings(self, sensitivity: float, selected_products: List[str]) -> bool:
        """Update settings on backend"""
        try:
            data = {
                "sensitivity": sensitivity,
                "selected_products": selected_products
            }
            
            response = requests.put(
                f"{self.settings_endpoint}/settings",
                json=data,
                headers=self.headers,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating settings: {e}")
            return False

    def validate_settings(self, sensitivity: float, selected_products: List[str]) -> Dict:
        """Validate settings before saving"""
        try:
            data = {
                "sensitivity": sensitivity,
                "selected_products": selected_products
            }
            
            response = requests.post(
                f"{self.settings_endpoint}/settings/validate",
                json=data,
                headers=self.headers,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error validating settings: {e}")
            return {"valid": False, "message": str(e)}