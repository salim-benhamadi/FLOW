# File: src/backend/api/v1/routers/metrics.py

from fastapi import APIRouter, HTTPException
from typing import Optional
import logging
from backend.db.database import DatabaseConnection
from typing import Dict

router = APIRouter()
db = DatabaseConnection()
logger = logging.getLogger(__name__)

@router.get("/model")
async def get_model_metrics(days: Optional[int] = 7):
    """Get model performance metrics"""
    try:
        query = """
            SELECT 
                accuracy,
                confidence,
                error_rate,
                model_version,
                model_path,
                training_reason,
                status,
                training_duration,
                created_at
            FROM model_metrics
            WHERE created_at >= NOW() - INTERVAL ':days days'
            ORDER BY created_at DESC
        """
        return await db.execute_query(query, {'days': days})
    except Exception as e:
        logger.error(f"Error getting model metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/distribution")
async def get_distribution_metrics(days: int = 30):
    """Get distribution of model performance metrics"""
    try:
        query = """
            SELECT 
                status,
                COUNT(*) as count,
                AVG(accuracy) as avg_accuracy,
                AVG(confidence) as avg_confidence,
                MIN(created_at) as first_seen,
                MAX(created_at) as last_seen
            FROM model_metrics
            GROUP BY status
        """
        return await db.execute_query(query)
    except Exception as e:
        logger.error(f"Error getting distribution metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/distribution")
async def get_distribution_metrics(days: int = 30):
    """Get distribution of model performance metrics for specified days"""
    try:
        query = """
            WITH daily_metrics AS (
                SELECT 
                    status,
                    DATE(created_at) as date,
                    AVG(accuracy) as avg_accuracy,
                    AVG(confidence) as avg_confidence,
                    AVG(error_rate) as avg_error_rate,
                    COUNT(*) as count
                FROM model_metrics
                WHERE created_at >= NOW() - INTERVAL ':days days'
                GROUP BY status, DATE(created_at)
            )
            SELECT 
                status,
                date,
                avg_accuracy,
                avg_confidence,
                avg_error_rate,
                count,
                MIN(date) OVER (PARTITION BY status) as first_seen,
                MAX(date) OVER (PARTITION BY status) as last_seen
            FROM daily_metrics
            ORDER BY date DESC, status
        """
        return await db.execute_query(query, {'days': days})
    except Exception as e:
        logger.error(f"Error getting distribution metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trend")
async def get_metrics_trend(days: int = 30):
    """Get trend analysis of metrics over time"""
    try:
        query = """
            WITH daily_stats AS (
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as total_trainings,
                    AVG(accuracy) as avg_accuracy,
                    AVG(confidence) as avg_confidence,
                    AVG(error_rate) as avg_error_rate
                FROM model_metrics
                WHERE created_at >= NOW() - INTERVAL ':days days'
                GROUP BY DATE(created_at)
            )
            SELECT * FROM daily_stats
            ORDER BY date DESC
        """
        return await db.execute_query(query, {'days': days})
    except Exception as e:
        logger.error(f"Error getting metrics trend: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/model")
async def save_model_metrics(metrics_data: Dict):
    """Save new model metrics"""
    try:
        metrics_id = await db.save_model_metrics(metrics_data)
        return {"metrics_id": metrics_id}
    except Exception as e:
        logger.error(f"Error saving model metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))