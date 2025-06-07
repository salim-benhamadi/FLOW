from typing import List, Optional, Dict
from datetime import datetime
from backend.db.database import DatabaseConnection
from backend.core.config import get_settings

class FeedbackService:
    def __init__(self):
        self.db = DatabaseConnection()
        self.settings = get_settings()

    async def store_feedback(self, feedback_data: dict) -> dict:
        """Store feedback in database"""
        query = """
        INSERT INTO model_feedback 
        (test_name, feedback_type, comment, confidence, created_at)
        VALUES (%(test_name)s, %(feedback_type)s, %(comment)s, %(confidence)s, %(created_at)s)
        RETURNING id
        """
        feedback_data['created_at'] = datetime.now()
        
        try:
            result = await self.db.execute_query(query, feedback_data)
            feedback_data['id'] = result[0]['id']
            return feedback_data
        except Exception as e:
            raise Exception(f"Error storing feedback: {str(e)}")

    async def get_feedback(
        self, 
        test_name: Optional[str] = None,
        feedback_type: Optional[str] = None,
        limit: int = 100
    ) -> List[dict]:
        """Get feedback history with optional filters"""
        query = """
        SELECT * FROM model_feedback 
        WHERE 1=1
        """
        params = {}
        
        if test_name:
            query += " AND test_name = %(test_name)s"
            params['test_name'] = test_name
            
        if feedback_type:
            query += " AND feedback_type = %(feedback_type)s"
            params['feedback_type'] = feedback_type
            
        query += " ORDER BY created_at DESC LIMIT %(limit)s"
        params['limit'] = limit
        
        try:
            return await self.db.execute_query(query, params)
        except Exception as e:
            raise Exception(f"Error retrieving feedback: {str(e)}")

    async def get_feedback_stats(self) -> Dict:
        """Get feedback statistics"""
        query = """
        SELECT 
            feedback_type,
            COUNT(*) as count,
            AVG(confidence) as avg_confidence
        FROM model_feedback
        GROUP BY feedback_type
        """
        
        try:
            results = await self.db.execute_query(query)
            return {
                'total_feedback': sum(r['count'] for r in results),
                'by_type': {r['feedback_type']: {
                    'count': r['count'],
                    'avg_confidence': r['avg_confidence']
                } for r in results}
            }
        except Exception as e:
            raise Exception(f"Error getting feedback stats: {str(e)}")

    async def check_retraining_needed(self) -> bool:
        """Check if model retraining is needed based on feedback"""
        query = """
        SELECT 
            COUNT(*) as total_feedback,
            AVG(CASE WHEN feedback_type = 'incorrect' THEN 1 ELSE 0 END) as error_rate
        FROM model_feedback
        WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
        """
        
        try:
            result = await self.db.execute_query(query)
            return (
                result[0]['total_feedback'] >= self.settings.MIN_FEEDBACK_FOR_RETRAIN or
                result[0]['error_rate'] >= self.settings.ERROR_RATE_THRESHOLD
            )
        except Exception as e:
            raise Exception(f"Error checking retraining status: {str(e)}")