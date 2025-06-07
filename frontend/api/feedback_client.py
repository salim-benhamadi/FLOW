# File: src/frontend/api/client.py

from typing import List, Dict, Any, Optional
import httpx
import asyncio
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class FeedbackClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = None
        self.client_lock = asyncio.Lock()
        self._closed = False

    async def _get_client(self):
        """Get or create HTTP client with safety checks"""
        if self._closed:
            raise RuntimeError("FeedbackClient is closed")
            
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

    # Feedback Management Methods
    async def submit_feedback(self, feedback_data: Dict) -> Dict:
        """
        Submit feedback to the API
        """
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
        """Get specific feedback entry"""
        try:
            return await self._make_request(
                "GET",
                f"/api/v1/feedback/{feedback_id}"
            )
        except Exception as e:
            logger.error(f"Error getting feedback: {str(e)}")
            raise
    
    async def get_all_feedback(self) -> Dict:
        """Get all feedback entry"""
        try:
            return await self._make_request(
                "GET",
                f"/api/v1/feedback/all"
            )
        except Exception as e:
            logger.error(f"Error getting feedback: {str(e)}")
            raise

    async def get_pending_feedback(
        self,
        limit: int = 10,
        severity: Optional[str] = None
    ) -> List[Dict]:
        """Get pending feedback entries"""
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
        """Update feedback status"""
        try:
            return await self._make_request(
                "PUT",
                f"/api/v1/feedback/{feedback_id}/status",
                params={'status': status}
            )
        except Exception as e:
            logger.error(f"Error updating feedback status: {str(e)}")
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