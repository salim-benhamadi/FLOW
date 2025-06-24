# frontend/api/client.py
from typing import List, Dict, Any, Optional, Union
import httpx
import asyncio
from datetime import datetime
import logging
from pathlib import Path
import json
from api.api_config import (
    get_api_base_url, 
    get_api_timeout, 
    get_api_verify_ssl, 
    get_api_headers,
    is_production
)

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self, base_url: Optional[str] = None):
        # Use provided URL or get from config
        self.base_url = base_url or get_api_base_url()
        self.timeout = get_api_timeout()
        self.verify_ssl = get_api_verify_ssl()
        self.headers = get_api_headers()
        
        self.client = None
        self.client_lock = asyncio.Lock()
        self._closed = False
        
        # Log configuration (but not in production)
        if not is_production():
            logger.info(f"APIClient initialized with:")
            logger.info(f"  Base URL: {self.base_url}")
            logger.info(f"  Timeout: {self.timeout}s")
            logger.info(f"  SSL Verify: {self.verify_ssl}")

    async def _get_client(self):
        """Get or create HTTP client with safety checks"""
        if self._closed:
            raise RuntimeError("APIClient is closed")
            
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
        """Make HTTP request with proper error handling"""
        client = await self._get_client()
        try:
            # Add some logging for debugging
            if not is_production():
                logger.debug(f"Making {method} request to {url}")
                
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            
            # Handle different response types
            content_type = response.headers.get('content-type', '')
            if 'application/json' in content_type:
                return response.json()
            else:
                return response.text
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during {method} {url}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response content: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error during {method} {url}: {str(e)}")
            raise

    # =================
    # Health & Status
    # =================
    
    async def health_check(self) -> Dict:
        """Check if the backend is healthy"""
        try:
            return await self._make_request("GET", "/health")
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            raise

    async def get_api_info(self) -> Dict:
        """Get API information and version"""
        try:
            return await self._make_request("GET", "/")
        except Exception as e:
            logger.error(f"Error getting API info: {str(e)}")
            raise

    # =================
    # Distribution Analysis
    # =================
    
    async def analyze_distribution(
        self,
        file_data: bytes,
        selected_items: Optional[List[str]] = None
    ) -> Dict:
        """Analyze distribution similarity from uploaded file"""
        try:
            files = {'file': ('upload.eff', file_data, 'application/octet-stream')}
            data = {}
            if selected_items:
                data['selected_items'] = selected_items
                
            return await self._make_request(
                "POST",
                "/api/v1/analyze/distribution",
                files=files,
                data=data
            )
        except Exception as e:
            logger.error(f"Error analyzing distribution: {str(e)}")
            raise

    async def compare_distributions(
        self,
        input_id: str,
        reference_id: str
    ) -> Dict:
        """Compare two specific distributions"""
        try:
            return await self._make_request(
                "GET",
                f"/api/v1/analyze/comparison/{input_id}",
                params={'reference_id': reference_id}
            )
        except Exception as e:
            logger.error(f"Error comparing distributions: {str(e)}")
            raise

    # =================
    # Model Settings Management
    # =================
    
    async def get_model_settings(self) -> Dict:
        """Get current model settings"""
        try:
            return await self._make_request("GET", "/api/v1/settings/settings")
        except Exception as e:
            logger.error(f"Error getting model settings: {str(e)}")
            raise

    async def update_model_settings(self, settings: Dict) -> Dict:
        """Update model settings"""
        try:
            return await self._make_request(
                "PUT",
                "/api/v1/settings/settings",
                json=settings
            )
        except Exception as e:
            logger.error(f"Error updating model settings: {str(e)}")
            raise

    async def get_settings_history(self) -> List[Dict]:
        """Get settings change history"""
        try:
            return await self._make_request("GET", "/api/v1/settings/settings/history")
        except Exception as e:
            logger.error(f"Error getting settings history: {str(e)}")
            raise

    async def validate_settings(self, settings: Dict) -> Dict:
        """Validate settings before applying"""
        try:
            return await self._make_request(
                "POST",
                "/api/v1/settings/settings/validate",
                json=settings
            )
        except Exception as e:
            logger.error(f"Error validating settings: {str(e)}")
            raise

    # =================
    # Reference Data Management
    # =================
    
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

    async def upload_reference_data(self, file_path: Path) -> Dict:
        """Upload reference data file"""
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (file_path.name, f.read(), 'application/octet-stream')}
            
            return await self._make_request(
                "POST",
                "/api/v1/reference/upload",
                files=files
            )
        except Exception as e:
            logger.error(f"Error uploading reference data: {str(e)}")
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

    # =================
    # Input Data Management
    # =================
    
    async def get_input_data_list(self) -> List[Dict]:
        """Get list of all input data"""
        try:
            return await self._make_request("GET", "/api/v1/input/list")
        except Exception as e:
            logger.error(f"Error getting input data list: {str(e)}")
            return []

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

    async def upload_input_data(self, file_path: Path) -> Dict:
        """Upload input data file"""
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

    # =================
    # Feedback Management
    # =================
    
    async def submit_feedback(self, feedback_data: Dict) -> Dict:
        """Submit feedback to the API"""
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
    
    async def get_all_feedback(self, limit: int = 50, offset: int = 0) -> Dict:
        """Get all feedback entries with pagination"""
        try:
            return await self._make_request(
                "GET",
                "/api/v1/feedback/all",
                params={'limit': limit, 'offset': offset}
            )
        except Exception as e:
            logger.error(f"Error getting all feedback: {str(e)}")
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

    # =================
    # Metrics Management
    # =================
    
    async def get_model_metrics(self, days: int = 7) -> List[Dict]:
        """Get model performance metrics"""
        try:
            return await self._make_request(
                "GET",
                "/api/v1/metrics/model",
                params={'days': days}
            )
        except Exception as e:
            logger.error(f"Error getting model metrics: {str(e)}")
            return []

    async def get_distribution_metrics(self, days: int = 30) -> List[Dict]:
        """Get distribution metrics"""
        try:
            return await self._make_request(
                "GET",
                "/api/v1/metrics/distribution",
                params={'days': days}
            )
        except Exception as e:
            logger.error(f"Error getting distribution metrics: {str(e)}")
            return []

    async def save_model_metrics(self, metrics_data: Dict) -> Dict:
        """Save model performance metrics"""
        try:
            return await self._make_request(
                "POST",
                "/api/v1/metrics/model",
                json=metrics_data
            )
        except Exception as e:
            logger.error(f"Error saving model metrics: {str(e)}")
            raise

    async def get_metrics_trend(self, days: int = 30) -> List[Dict]:
        """Get trend analysis of metrics over time"""
        try:
            return await self._make_request(
                "GET",
                "/api/v1/metrics/trend",
                params={'days': days}
            )
        except Exception as e:
            logger.error(f"Error getting metrics trend: {str(e)}")
            return []

    # =================
    # Model Training Management
    # =================
    
    async def start_model_retraining(self, training_params: Optional[Dict] = None) -> Dict:
        """Start model retraining process"""
        try:
            data = training_params or {}
            return await self._make_request(
                "POST",
                "/api/v1/training/start",
                json=data
            )
        except Exception as e:
            logger.error(f"Error starting model retraining: {str(e)}")
            raise

    async def get_training_status(self) -> Dict:
        """Get current training status"""
        try:
            return await self._make_request("GET", "/api/v1/training/status")
        except Exception as e:
            logger.error(f"Error getting training status: {str(e)}")
            raise

    async def get_training_history(self, limit: int = 20) -> List[Dict]:
        """Get training history"""
        try:
            return await self._make_request(
                "GET",
                "/api/v1/training/history",
                params={'limit': limit}
            )
        except Exception as e:
            logger.error(f"Error getting training history: {str(e)}")
            return []

    async def stop_training(self) -> Dict:
        """Stop current training process"""
        try:
            return await self._make_request("POST", "/api/v1/training/stop")
        except Exception as e:
            logger.error(f"Error stopping training: {str(e)}")
            raise
    
    async def get_model_versions(self) -> List[str]:
        """Get list of all model versions"""
        try:
            response = await self._make_request('GET', '/api/model-versions')
            return response.get('versions', [])
        except Exception as e:
            logger.error(f"Error fetching model versions: {e}")
            return []
    
    async def get_model_metrics(self, version: str = None) -> List[Dict]:
        """Get metrics for a specific model version"""
        try:
            params = {'version': version} if version else {}
            response = await self._make_request('GET', '/api/model-metrics', params=params)
            return response.get('metrics', [])
        except Exception as e:
            logger.error(f"Error fetching model metrics: {e}")
            return []
    
    async def get_version_comparison_data(self) -> List[Dict]:
        """Get comparison data across all model versions"""
        try:
            response = await self._make_request('GET', '/api/model-versions/comparison')
            return response.get('comparison_data', [])
        except Exception as e:
            logger.error(f"Error fetching version comparison: {e}")
            return []
    
    async def get_training_history(self) -> List[Dict]:
        """Get model training history"""
        try:
            response = await self._make_request('GET', '/api/training-history')
            return response.get('history', [])
        except Exception as e:
            logger.error(f"Error fetching training history: {e}")
            return []
    
    async def compare_distributions(self, new_data: Dict, reference_id: str) -> Dict:
        """Compare distributions between new data and reference"""
        try:
            payload = {
                'new_data': new_data,
                'reference_id': reference_id
            }
            response = await self._make_request('POST', '/api/compare-distributions', data=payload)
            return response
        except Exception as e:
            logger.error(f"Error comparing distributions: {e}")
            return {'confidence': 0, 'match_score': 0}
    
    async def retrain_model_with_data(self, training_data: Dict) -> Dict:
        """Trigger model retraining with specific data"""
        try:
            response = await self._make_request('POST', '/api/retrain-model', data=training_data)
            return response
        except Exception as e:
            logger.error(f"Error retraining model: {e}")
            raise
    
    async def update_model_metrics(self, metrics_data: Dict) -> bool:
        """Update metrics for a model version"""
        try:
            version = metrics_data.get('version', 'v1')
            response = await self._make_request('PUT', f'/api/model-metrics/{version}', data=metrics_data)
            return response.get('success', False)
        except Exception as e:
            logger.error(f"Error updating model metrics: {e}")
            return False
    
    async def create_model_version(self, version_data: Dict) -> Dict:
        """Create a new model version entry"""
        try:
            response = await self._make_request('POST', '/api/model-versions', data=version_data)
            return response
        except Exception as e:
            logger.error(f"Error creating model version: {e}")
            raise
    
    async def get_vamos_analysis(self, reference_id: str) -> Dict:
        """Get VAMOS analysis results for reference data"""
        try:
            response = await self._make_request('GET', f'/api/vamos-analysis/{reference_id}')
            return response
        except Exception as e:
            logger.error(f"Error fetching VAMOS analysis: {e}")
            return {}
    
    async def log_training_event(self, event_data: Dict) -> bool:
        """Log a training event"""
        try:
            response = await self._make_request('POST', '/api/training-events', data=event_data)
            return response.get('success', False)
        except Exception as e:
            logger.error(f"Error logging training event: {e}")
            return False
    # =================
    # File Processing Utilities
    # =================
    
    async def process_eff_file(
        self,
        file_path: Path,
        product: str,
        lot: str,
        insertion: str
    ) -> Dict:
        """Process EFF file with metadata"""
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Create form data
            files = {'file': (file_path.name, file_data, 'application/octet-stream')}
            data = {
                'product': product,
                'lot': lot,
                'insertion': insertion
            }
            
            return await self._make_request(
                "POST",
                "/api/v1/process/eff",
                files=files,
                data=data
            )
        except Exception as e:
            logger.error(f"Error processing EFF file: {str(e)}")
            raise

    # =================
    # Batch Operations
    # =================
    
    async def batch_analyze(self, file_list: List[Path]) -> List[Dict]:
        """Analyze multiple files in batch"""
        results = []
        for file_path in file_list:
            try:
                with open(file_path, 'rb') as f:
                    result = await self.analyze_distribution(f.read())
                    result['filename'] = file_path.name
                    results.append(result)
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
                results.append({
                    'filename': file_path.name,
                    'error': str(e),
                    'success': False
                })
        return results

    # =================
    # Utility Methods
    # =================
    
    async def test_connection(self) -> bool:
        """Test if connection to backend is working"""
        try:
            await self.health_check()
            return True
        except Exception:
            return False

    def get_base_url(self) -> str:
        """Get the current base URL"""
        return self.base_url

    def is_connected(self) -> bool:
        """Check if client has an active connection"""
        return self.client is not None and not self._closed

    # =================
    # Resource Management
    # =================
    
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
        """Async context manager entry"""
        await self._get_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    def __del__(self):
        """Destructor to ensure cleanup"""
        if not self._closed and self.client:
            # Create a simple cleanup task for the destructor
            try:
                if hasattr(asyncio, 'get_running_loop'):
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.close())
            except Exception:
                # If we can't schedule cleanup, at least mark as closed
                self._closed = True