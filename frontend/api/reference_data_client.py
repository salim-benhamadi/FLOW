import requests
from typing import List, Dict, Optional
import logging
from api.api_config import get_api_base_url, get_api_headers, get_api_timeout, get_api_verify_ssl

logger = logging.getLogger(__name__)

class ReferenceDataClient:
    def __init__(self):
        self.base_url = get_api_base_url()
        self.headers = get_api_headers()
        self.timeout = get_api_timeout()
        self.verify_ssl = get_api_verify_ssl()
        self.reference_endpoint = f"{self.base_url}/api/v1/reference"

    def get_available_reference_data(self) -> Dict:
        """Get available reference data structure from cloud"""
        try:
            response = requests.get(
                f"{self.reference_endpoint}/available",
                headers=self.headers,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching available reference data: {e}")
            # Return empty structure, let the UI handle the error display
            return {"products": {}}

    def get_reference_list(self) -> List[Dict]:
        """Get list of all reference data entries"""
        try:
            response = requests.get(
                f"{self.reference_endpoint}/list",
                headers=self.headers,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching reference list: {e}")
            raise

    def search_reference_data(self, query: str) -> Dict:
        """Search reference data based on query"""
        try:
            response = requests.get(
                f"{self.reference_endpoint}/search",
                params={"q": query},
                headers=self.headers,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error searching reference data: {e}")
            return {"products": {}}

    def get_reference_files(self, products: List[str], lots: Dict[str, List[str]], 
                          insertions: Dict[str, Dict[str, List[str]]]) -> List[str]:
        """Get reference file paths for selected products/lots/insertions"""
        try:
            data = {
                "products": products,
                "lots": lots,
                "insertions": insertions
            }
            
            response = requests.post(
                f"{self.reference_endpoint}/files",
                json=data,
                headers=self.headers,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            return response.json().get("files", [])
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching reference files: {e}")
            return []

    def upload_reference_data(self, file_path: str) -> Dict:
        """Upload reference data file"""
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(
                    f"{self.reference_endpoint}/upload",
                    files=files,
                    headers=self.headers,
                    timeout=self.timeout,
                    verify=self.verify_ssl
                )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error uploading reference data: {e}")
            raise

    def get_reference_data_structure(self) -> Dict:
        """Transform reference list into hierarchical structure for UI"""
        try:
            reference_list = self.get_reference_list()
            
            # Transform flat list into hierarchical structure
            products = {}
            for ref in reference_list:
                product = ref.get('product', '')
                lot = ref.get('lot', '')
                insertion = ref.get('insertion', '')
                
                if product not in products:
                    products[product] = {"lots": {}}
                
                if lot not in products[product]["lots"]:
                    products[product]["lots"][lot] = []
                
                if insertion and insertion not in products[product]["lots"][lot]:
                    products[product]["lots"][lot].append(insertion)
            
            return {"products": products}
        except Exception as e:
            logger.error(f"Error building reference data structure: {e}")
            return {"products": {}}