from fastapi import APIRouter, HTTPException
from typing import Dict
import logging
from backend.db.database import DatabaseConnection
from backend.core.config import get_settings

router = APIRouter()
db = DatabaseConnection()
settings = get_settings()
logger = logging.getLogger(__name__)

@router.get("/settings")
async def get_current_settings():
    """Get current model settings"""
    try:
        model_settings = await db.get_model_settings()
        if not model_settings:
            return settings.DEFAULT_MODEL_SETTINGS
        return model_settings
    except Exception as e:
        logger.error(f"Error getting settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/settings")
async def update_settings(settings_data: Dict):
    """Update model settings"""
    try:
        success = await db.update_model_settings(settings_data)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to update settings")
        return {"status": "updated"}
    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/settings/history")
async def get_settings_history():
    """Get history of settings changes"""
    try:
        history = await db.execute_query("""
            SELECT 
                id,
                confidence_threshold,
                critical_issue_weight,
                high_priority_weight,
                normal_priority_weight,
                auto_retrain,
                retraining_schedule,
                created_at,
                updated_at
            FROM model_settings
            ORDER BY created_at DESC
        """)
        return history
    except Exception as e:
        logger.error(f"Error getting settings history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/settings/validate")
async def validate_settings(settings_data: Dict):
    """Validate settings before applying"""
    try:
        # Validate confidence threshold
        if 'confidence_threshold' in settings_data:
            if not 0 <= settings_data['confidence_threshold'] <= 1:
                raise ValueError("Confidence threshold must be between 0 and 1")

        # Validate weights
        for weight_type in ['critical_issue_weight', 'high_priority_weight', 'normal_priority_weight']:
            if weight_type in settings_data:
                if not 0 <= settings_data[weight_type] <= 10:
                    raise ValueError(f"{weight_type} must be between 0 and 10")

        return {"valid": True, "message": "Settings are valid"}
    except Exception as e:
        return {"valid": False, "message": str(e)}