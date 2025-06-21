from typing import List, Dict, Any, Optional
import httpx
import asyncio
from datetime import datetime
import logging
from pathlib import Path
from resources.config.api_config import (
    get_api_base_url, 
    get_api_timeout, 
    get_api_verify_ssl, 
    get_api_headers,
    is_production
)

logger = logging.getLogger(__name__)

class FeedbackClient:
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
            raise RuntimeError("FeedbackClient is closed")
            
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

    async def submit_feedback(self, feedback_data: Dict) -> Dict:
        try:
            return await self._make_request(
                "POST",
                "/api/v1/feedback/submit",
                json=feedback_data
            )
        except Exception as e:
            logger.error(f"Error submitting feedback: {str(e)}")
            raise
        
    async def get_feedback(self, feedback_id: int) -> Dict:
        try:
            return await self._make_request(
                "GET",
                f"/api/v1/feedback/{feedback_id}"
            )
        except Exception as e:
            logger.error(f"Error getting feedback: {str(e)}")
            raise
    
    async def get_all_feedback(self, limit: int = 50, offset: int = 0) -> Dict:
        try:
            return await self._make_request(
                "GET",
                "/api/v1/feedback/all",
                params={'limit': limit, 'offset': offset}
            )
        except Exception as e:
            logger.error(f"Error getting feedback: {str(e)}")
            raise

    async def get_pending_feedback(
        self,
        limit: int = 10,
        severity: Optional[str] = None
    ) -> List[Dict]:
        try:
            params = {'limit': limit}
            if severity:
                params['severity'] = severity

            return await self._make_request(
                "GET",
                "/api/v1/feedback/pending",
                params=params
            )
        except Exception as e:
            logger.error(f"Error getting pending feedback: {str(e)}")
            raise

    async def update_feedback_status(
        self, 
        feedback_id: int, 
        status: str
    ) -> Dict:
        try:
            return await self._make_request(
                "PUT",
                f"/api/v1/feedback/{feedback_id}/status",
                params={'status': status}
            )
        except Exception as e:
            logger.error(f"Error updating feedback status: {str(e)}")
            raise

    async def search_feedback(
        self,
        test_name: Optional[str] = None,
        lot: Optional[str] = None,
        severity: Optional[str] = None,
        status: Optional[str] = None,
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
            if severity:
                params['severity'] = severity
            if status:
                params['status'] = status
            if start_date:
                params['start_date'] = start_date.isoformat()
            if end_date:
                params['end_date'] = end_date.isoformat()

            return await self._make_request(
                "GET",
                "/api/v1/feedback/search",
                params=params
            )
        except Exception as e:
            logger.error(f"Error searching feedback: {str(e)}")
            raise

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