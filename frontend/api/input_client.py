# File: src/frontend/api/input_client.py

from typing import List, Dict, Any, Optional
import httpx
import asyncio
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class InputClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = None
        self.client_lock = asyncio.Lock()
        self._closed = False

    async def _get_client(self):
        """Get or create HTTP client with safety checks"""
        if self._closed:
            raise RuntimeError("InputClient is closed")
            
        async with self.client_lock:
            if self.client is None:
                self.client = httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=30.0,
                    headers={"Accept": "application/json"},
                    http2=False
                )
            return self.client

    async def _make_request(self, method: str, url: str, **kwargs):
        """Make HTTP request with proper error handling"""
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

    # Input Data Management Methods
    async def upload_input_data(self, file_path: Path) -> Dict:
        """Upload input data file"""
        try:
            files = {'file': open(file_path, 'rb')}
            return await self._make_request(
                "POST",
                "/api/v1/input/upload",
                files=files
            )
        except Exception as e:
            logger.error(f"Error uploading input data: {str(e)}")
            raise

    async def save_input_data(self, input_data: Dict) -> Dict:
        """Save input data and measurements"""
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
        """Get specific input data entry with measurements"""
        try:
            return await self._make_request(
                "GET",
                f"/api/v1/input/{input_id}"
            )
        except Exception as e:
            logger.error(f"Error getting input data: {str(e)}")
            raise

    async def list_input_data(self) -> List[Dict]:
        """Get list of all input data"""
        try:
            return await self._make_request(
                "GET",
                "/api/v1/input/list"
            )
        except Exception as e:
            logger.error(f"Error listing input data: {str(e)}")
            raise

    async def delete_input_data(self, input_id: str) -> Dict:
        """Delete input data entry and its measurements"""
        try:
            return await self._make_request(
                "DELETE",
                f"/api/v1/input/{input_id}"
            )
        except Exception as e:
            logger.error(f"Error deleting input data: {str(e)}")
            raise

    async def get_input_measurements(self, input_id: str) -> List[Dict]:
        """Get measurements for specific input data entry"""
        try:
            return await self._make_request(
                "GET",
                f"/api/v1/input/{input_id}/measurements"
            )
        except Exception as e:
            logger.error(f"Error getting input measurements: {str(e)}")
            raise

    # Resource Management
    async def close(self):
        """Close client resources safely"""
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