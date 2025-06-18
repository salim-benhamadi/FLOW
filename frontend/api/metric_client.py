from typing import List, Dict, Optional
import httpx
import asyncio
import logging
from config.api_config import (
    get_api_base_url, 
    get_api_timeout, 
    get_api_verify_ssl, 
    get_api_headers,
    is_production
)

logger = logging.getLogger(__name__)

class MetricClient:
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
            raise RuntimeError("MetricClient is closed")
            
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

    async def get_model_metrics(self, days: int = 7) -> List[Dict]:
        try:
            return await self._make_request(
                "GET",
                "/api/v1/metrics/model",
                params={'days': days}
            )
        except Exception as e:
            logger.error(f"Error getting model metrics: {e}")
            return []

    async def save_model_metrics(self, metrics_data: Dict) -> Dict:
        try:
            return await self._make_request(
                "POST",
                "/api/v1/metrics/model",
                json=metrics_data
            )
        except Exception as e:
            logger.error(f"Error saving model metrics: {e}")
            raise

    async def get_distribution_metrics(self, days: int = 30) -> List[Dict]:
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
        try:
            return await self._make_request(
                "GET",
                "/api/v1/metrics/trend",
                params={'days': days}
            )
        except Exception as e:
            logger.error(f"Error getting metrics trend: {e}")
            return []

    async def get_api_usage_metrics(self, days: int = 30) -> List[Dict]:
        try:
            return await self._make_request(
                "GET",
                "/api/v1/metrics/usage",
                params={'days': days}
            )
        except Exception as e:
            logger.error(f"Error getting API usage metrics: {e}")
            return []

    async def get_performance_metrics(self, days: int = 7) -> Dict:
        try:
            return await self._make_request(
                "GET",
                "/api/v1/metrics/performance",
                params={'days': days}
            )
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}

    async def get_error_metrics(self, days: int = 7) -> List[Dict]:
        try:
            return await self._make_request(
                "GET",
                "/api/v1/metrics/errors",
                params={'days': days}
            )
        except Exception as e:
            logger.error(f"Error getting error metrics: {e}")
            return []

    async def close(self):
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