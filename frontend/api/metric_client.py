# File: src/frontend/api/metric_client.py

from typing import List, Dict, Optional
import httpx
import asyncio
import logging

logger = logging.getLogger(__name__)

class MetricClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = None
        self.client_lock = asyncio.Lock()
        self._closed = False

    async def _get_client(self):
        """Get or create HTTP client with safety checks"""
        if self._closed:
            raise RuntimeError("APIClient is closed")
            
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

    async def get_model_metrics(self, days: int = 7) -> List[Dict]:
        """Get model performance metrics"""
        try:
            return await self._make_request(
                "GET",
                "/api/v1/metrics/model",
                params={'days': days}
            )
        except Exception as e:
            logger.error(f"Error getting model metrics: {e}")
            return []

    async def get_api_metrics(self, days: int = 7) -> Dict:
        """Get API usage metrics"""
        try:
            return await self._make_request(
                "GET",
                "/api/v1/metrics/api",
                params={'days': days}
            )
        except Exception as e:
            logger.error(f"Error getting API metrics: {e}")
            return {}

    async def save_model_metrics(self, metrics_data: Dict) -> Dict:
        """Save new model metrics"""
        try:
            # Validate required fields for model metrics
            required_fields = [
                'accuracy', 'confidence', 'error_rate', 'model_version',
                'model_path', 'training_reason', 'status', 'training_duration'
            ]
            
            missing_fields = [field for field in required_fields 
                            if field not in metrics_data]
            
            if missing_fields:
                raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

            return await self._make_request(
                "POST",
                "/api/v1/metrics/model",
                json=metrics_data
            )
        except Exception as e:
            logger.error(f"Error saving model metrics: {e}")
            raise

    async def get_distribution_metrics(self, days: int = 30) -> List[Dict]:
        """Get metrics about distribution types"""
        try:
            return await self._make_request(
                "GET",
                "/api/v1/metrics/distribution",
                params={'days': days}
            )
        except Exception as e:
            logger.error(f"Error getting distribution metrics: {e}")
            return []

    async def get_metrics_trend(self, days: int = 30) -> List[Dict]:
        """Get trend analysis of metrics over time"""
        try:
            return await self._make_request(
                "GET",
                "/api/v1/metrics/trend",
                params={'days': days}
            )
        except Exception as e:
            logger.error(f"Error getting metrics trend: {e}")
            return []

    async def close(self):
        """Close client resources safely"""
        if not self._closed:
            self._closed = True
            if self.client:
                try:
                    await self.client.aclose()
                except Exception as e:
                    logger.error(f"Error closing client: {e}")
                finally:
                    self.client = None

    async def __aenter__(self):
        await self._get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()