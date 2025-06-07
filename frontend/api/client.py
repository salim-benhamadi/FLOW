from typing import List, Dict, Any, Optional
import httpx
import asyncio
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class APIClient:
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

    # Distribution Analysis
    async def analyze_distribution(
        self,
        file_data: bytes,
        selected_items: List[str],
        lot: str,
        insertion: str
    ) -> Dict:
        """Analyze distribution similarity"""
        try:
            files = {'file': file_data}
            params = {
                'selected_items': selected_items,
                'lot': lot,
                'insertion': insertion
            }
            return await self._make_request(
                "POST",
                "/api/v1/analyze/distribution",
                files=files,
                params=params
            )
        except Exception as e:
            logger.error(f"Error analyzing distribution: {str(e)}")
            raise

    async def get_analysis_result(self, analysis_id: str) -> Dict:
        """Get specific analysis result"""
        try:
            return await self._make_request(
                "GET",
                f"/api/v1/analyze/analysis/{analysis_id}"
            )
        except Exception as e:
            logger.error(f"Error getting analysis result: {str(e)}")
            raise

    async def get_recent_analyses(
        self,
        limit: int = 10,
        lot: Optional[str] = None,
        test_name: Optional[str] = None
    ) -> List[Dict]:
        """Get recent analysis results"""
        try:
            params = {'limit': limit}
            if lot:
                params['lot'] = lot
            if test_name:
                params['test_name'] = test_name

            return await self._make_request(
                "GET",
                "/api/v1/analyze/analysis/recent",
                params=params
            )
        except Exception as e:
            logger.error(f"Error getting recent analyses: {str(e)}")
            raise

    async def get_feedback(self, feedback_id: int) -> Dict:
        """Get specific feedback"""
        try:
            return await self._make_request(
                "GET",
                f"/api/v1/feedback/{feedback_id}"
            )
        except Exception as e:
            logger.error(f"Error getting feedback: {str(e)}")
            raise

    async def get_pending_feedback(
        self,
        limit: int = 10,
        severity: Optional[str] = None
    ) -> List[Dict]:
        """Get pending feedback"""
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

    async def update_feedback_status(self, feedback_id: int, status: str) -> Dict:
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
        """Search feedback with filters"""
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
    async def get_analysis_stats(self, days: int = 30) -> Dict:
        """Get analysis statistics"""
        try:
            return await self._make_request(
                "GET",
                "/api/v1/analyze/analysis/stats",
                params={'days': days}
            )
        except Exception as e:
            logger.error(f"Error getting analysis stats: {str(e)}")
            raise

    # Settings Management
    async def get_model_settings(self) -> Dict:
        """Get current model settings"""
        try:
            return await self._make_request("GET", "/api/v1/settings")
        except Exception as e:
            logger.error(f"Error getting model settings: {str(e)}")
            raise

    async def update_model_settings(self, settings: Dict) -> Dict:
        """Update model settings"""
        try:
            return await self._make_request(
                "PUT",
                "/api/v1/settings",
                json=settings
            )
        except Exception as e:
            logger.error(f"Error updating model settings: {str(e)}")
            raise

    async def get_settings_history(self) -> List[Dict]:
        """Get settings change history"""
        try:
            return await self._make_request("GET", "/api/v1/settings/history")
        except Exception as e:
            logger.error(f"Error getting settings history: {str(e)}")
            raise

    # Reference Data Management
    async def get_reference_data_list(self) -> List[Dict]:
        """Get list of all reference data"""
        try:
            return await self._make_request("GET", "/api/v1/reference/list")
        except Exception as e:
            logger.error(f"Error getting reference data list: {str(e)}")
            return []

    async def get_reference_data(self, reference_id: str) -> Dict:
        """Get specific reference data entry"""
        try:
            return await self._make_request(
                "GET",
                f"/api/v1/reference/{reference_id}"
            )
        except Exception as e:
            logger.error(f"Error getting reference data: {str(e)}")
            raise

    async def save_reference_data(self, data: Dict) -> Dict:
        """Save reference data"""
        try:
            return await self._make_request(
                "POST",
                "/api/v1/reference/save",
                json=data
            )
        except Exception as e:
            logger.error(f"Error saving reference data: {str(e)}")
            raise

    async def delete_reference_data(self, reference_id: str) -> Dict:
        """Delete reference data entry"""
        try:
            return await self._make_request(
                "DELETE",
                f"/api/v1/reference/{reference_id}"
            )
        except Exception as e:
            logger.error(f"Error deleting reference data: {str(e)}")
            raise

    async def upload_reference_data(self, file_path: str) -> Dict:
        """Upload reference data file"""
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                return await self._make_request(
                    "POST",
                    "/api/v1/reference/upload",
                    files=files
                )
        except Exception as e:
            logger.error(f"Error uploading reference data: {str(e)}")
            raise

    # Health Check
    async def check_health(self) -> Dict:
        """Check API health status"""
        try:
            return await self._make_request("GET", "/health")
        except Exception as e:
            logger.error(f"Error checking API health: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}

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
        await self._get_client()  # Ensure client is initialized
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # Model Training
    async def start_model_retraining(self) -> Dict:
        """Start model retraining process"""
        try:
            return await self._make_request("POST", "/api/v1/model/retrain")
        except Exception as e:
            logger.error(f"Error starting model retraining: {str(e)}")
            raise

    async def get_training_status(self) -> Dict:
        """Get current training status"""
        try:
            return await self._make_request("GET", "/api/v1/model/status")
        except Exception as e:
            logger.error(f"Error getting training status: {str(e)}")
            raise