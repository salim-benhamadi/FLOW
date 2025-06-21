from typing import List, Dict, Any, Optional
import httpx
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from resources.config.api_config import (
    get_api_base_url, 
    get_api_timeout, 
    get_api_verify_ssl, 
    get_api_headers,
    is_production
)

logger = logging.getLogger(__name__)

class InputClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or get_api_base_url()
        self.timeout = get_api_timeout()
        self.verify_ssl = get_api_verify_ssl()
        self.headers = get_api_headers()
        self.client = None
        self.client_lock = asyncio.Lock()
        self._closed = False

    async def _get_client(self):
        if self._closed:
            raise RuntimeError("InputClient is closed")
            
        async with self.client_lock:
            if self.client is None:
                self.client = httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=self.timeout,
                    headers=self.headers,
                    verify=self.verify_ssl,
                    http2=False
                )
            return self.client

    async def _make_request(self, method: str, url: str, **kwargs):
        client = await self._get_client()
        try:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during {method} {url}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error during {method} {url}: {str(e)}")
            raise

    async def upload_input_data(self, file_path: Path) -> Dict:
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f.read(), 'application/octet-stream')}
            return await self._make_request(
                "POST",
                "/api/v1/input/upload",
                files=files
            )
        except Exception as e:
            logger.error(f"Error uploading input data: {str(e)}")
            raise

    async def save_input_data(self, input_data: Dict) -> Dict:
        try:
            return await self._make_request(
                "POST",
                "/api/v1/input/save",
                json=input_data
            )
        except Exception as e:
            logger.error(f"Error saving input data: {str(e)}")
            raise

    async def get_input_data(self, input_id: str) -> Dict:
        try:
            return await self._make_request(
                "GET",
                f"/api/v1/input/{input_id}"
            )
        except Exception as e:
            logger.error(f"Error getting input data: {str(e)}")
            raise

    async def list_input_data(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        try:
            return await self._make_request(
                "GET",
                "/api/v1/input/list",
                params={'limit': limit, 'offset': offset}
            )
        except Exception as e:
            logger.error(f"Error listing input data: {str(e)}")
            return []

    async def delete_input_data(self, input_id: str) -> Dict:
        try:
            return await self._make_request(
                "DELETE",
                f"/api/v1/input/{input_id}"
            )
        except Exception as e:
            logger.error(f"Error deleting input data: {str(e)}")
            raise

    async def get_input_measurements(self, input_id: str) -> List[Dict]:
        try:
            return await self._make_request(
                "GET",
                f"/api/v1/input/{input_id}/measurements"
            )
        except Exception as e:
            logger.error(f"Error getting input measurements: {str(e)}")
            return []

    async def update_input_data(self, input_id: str, update_data: Dict) -> Dict:
        try:
            return await self._make_request(
                "PUT",
                f"/api/v1/input/{input_id}",
                json=update_data
            )
        except Exception as e:
            logger.error(f"Error updating input data: {str(e)}")
            raise

    async def search_input_data(
        self,
        test_name: Optional[str] = None,
        lot: Optional[str] = None,
        insertion: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict]:
        try:
            params = {'limit': limit}
            if test_name:
                params['test_name'] = test_name
            if lot:
                params['lot'] = lot
            if insertion:
                params['insertion'] = insertion
            if start_date:
                params['start_date'] = start_date.isoformat()
            if end_date:
                params['end_date'] = end_date.isoformat()

            return await self._make_request(
                "GET",
                "/api/v1/input/search",
                params=params
            )
        except Exception as e:
            logger.error(f"Error searching input data: {str(e)}")
            return []

    async def get_input_statistics(self, input_id: str) -> Dict:
        try:
            return await self._make_request(
                "GET",
                f"/api/v1/input/{input_id}/statistics"
            )
        except Exception as e:
            logger.error(f"Error getting input statistics: {str(e)}")
            return {}

    async def close(self):
        if not self._closed:
            self._closed = True
            if self.client:
                try:
                    await self.client.aclose()
                except Exception as e:
                    logger.error(f"Error closing client: {str(e)}")
                finally:
                    self.client = None

    async def __aenter__(self):
        await self._get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()