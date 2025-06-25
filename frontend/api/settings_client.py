import requests
from typing import List, Dict, Optional
import logging
from pathlib import Path
from api.api_config import get_api_base_url, get_api_headers, get_api_timeout, get_api_verify_ssl

logger = logging.getLogger(__name__)

class SettingsClient:
    def __init__(self):
        self.base_url = get_api_base_url()
        self.headers = get_api_headers()
        self.timeout = get_api_timeout()
        self.verify_ssl = get_api_verify_ssl()
        self.settings_endpoint = f"{self.base_url}/api/v1/settings"
        self.model_endpoint = f"{self.base_url}/api"

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
            return {"sensitivity": 0.5, "selected_products": [], "model_version": "v1"}
    
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

    # Model version methods
    def get_model_versions(self) -> List[str]:
        """Fetch available model versions from the cloud"""
        try:
            response = requests.get(
                f"{self.model_endpoint}/model-versions",
                headers=self.headers,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('versions', ['v1'])
            else:
                logger.error(f"Error fetching versions: {response.status_code}")
                return ['v1']  # Default fallback
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to API: {e}")
            return ['v1']  # Default fallback
    
    def get_model_info(self, version: str) -> Optional[Dict]:
        """Get detailed information about a specific model version"""
        try:
            response = requests.get(
                f"{self.model_endpoint}/model-versions/{version}",
                headers=self.headers,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            if response.status_code == 200:
                return response.json()
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching model info: {e}")
            return None
    
    def download_model(self, version: str, save_path: str) -> bool:
        """Download a specific model version from the cloud"""
        try:
            response = requests.get(
                f"{self.model_endpoint}/models/{version}/download",
                headers=self.headers,
                timeout=self.timeout,
                verify=self.verify_ssl,
                stream=True  # Important for downloading large files
            )
            if response.status_code == 200:
                # Create directory if it doesn't exist
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                
                # Write file in chunks to handle large files
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
            else:
                logger.error(f"Failed to download model: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading model: {e}")
            return False
    
    def get_latest_model_version(self) -> Optional[str]:
        """Get the latest model version available"""
        versions = self.get_model_versions()
        if versions:
            # Assuming versions are in format v1, v2, v3, etc.
            return sorted(versions, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0, reverse=True)[0]
        return None
    
    def check_model_update_available(self, current_version: str) -> bool:
        """Check if a newer model version is available"""
        latest_version = self.get_latest_model_version()
        if latest_version and current_version:
            try:
                latest_num = int(latest_version[1:]) if latest_version[1:].isdigit() else 0
                current_num = int(current_version[1:]) if current_version[1:].isdigit() else 0
                return latest_num > current_num
            except ValueError:
                return False
        return False