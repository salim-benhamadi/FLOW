from typing import Dict, Optional
from backend.db.database import DatabaseConnection
from backend.core.config import get_settings
from datetime import datetime

class SettingsService:
    def __init__(self):
        self.db = DatabaseConnection()
        self.settings = get_settings()

    async def get_model_settings(self) -> Dict:
        """Get current model settings"""
        query = """
        SELECT *
        FROM model_settings
        ORDER BY created_at DESC
        LIMIT 1
        """
        try:
            result = await self.db.execute_query(query)
            if result:
                return result[0]
            return {
                'confidence_threshold': 0.95,
                'feedback_weights': {
                    'correct': 1.0,
                    'incorrect': 2.0,
                    'uncertain': 0.5
                },
                'retraining_schedule': 'weekly',
                'auto_retrain': True
            }
        except Exception as e:
            raise Exception(f"Error retrieving model settings: {str(e)}")

    async def update_model_settings(self, settings_data: Dict) -> Dict:
        """Update model settings"""
        query = """
        INSERT INTO model_settings 
        (confidence_threshold, feedback_weights, retraining_schedule, auto_retrain, created_at)
        VALUES (
            %(confidence_threshold)s, 
            %(feedback_weights)s, 
            %(retraining_schedule)s, 
            %(auto_retrain)s,
            %(created_at)s
        )
        """
        try:
            settings_data['created_at'] = datetime.now()
            await self.db.execute_query(query, settings_data)
            return await self.get_model_settings()
        except Exception as e:
            raise Exception(f"Error updating model settings: {str(e)}")

    async def get_retraining_settings(self) -> Dict:
        """Get model retraining settings"""
        query = """
        SELECT *
        FROM retraining_settings
        ORDER BY created_at DESC
        LIMIT 1
        """
        try:
            result = await self.db.execute_query(query)
            if result:
                return result[0]
            return {
                'schedule': 'weekly',
                'min_feedback_count': 100,
                'error_rate_threshold': 0.2
            }
        except Exception as e:
            raise Exception(f"Error retrieving retraining settings: {str(e)}")

    async def update_retraining_settings(self, settings_data: Dict) -> Dict:
        """Update model retraining settings"""
        query = """
        INSERT INTO retraining_settings 
        (schedule, min_feedback_count, error_rate_threshold, created_at)
        VALUES (
            %(schedule)s,
            %(min_feedback_count)s,
            %(error_rate_threshold)s,
            %(created_at)s
        )
        """
        try:
            settings_data['created_at'] = datetime.now()
            await self.db.execute_query(query, settings_data)
            return await self.get_retraining_settings()
        except Exception as e:
            raise Exception(f"Error updating retraining settings: {str(e)}")

    async def trigger_retraining(self) -> Dict:
        """Manually trigger model retraining"""
        from backend.services.model_service import ModelService
        try:
            model_service = ModelService()
            await model_service.retrain_model()
            return {"status": "success", "message": "Model retraining triggered successfully"}
        except Exception as e:
            raise Exception(f"Error triggering model retraining: {str(e)}")