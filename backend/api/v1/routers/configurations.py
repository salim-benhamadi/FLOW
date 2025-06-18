from fastapi import APIRouter, HTTPException
from typing import Dict, List
from pydantic import BaseModel, Field
import logging
from backend.db.database import DatabaseConnection
from backend.core.config import get_settings

router = APIRouter()
db = DatabaseConnection()
settings = get_settings()
logger = logging.getLogger(__name__)

class UpdateSettingsRequest(BaseModel):
    sensitivity: float = Field(ge=0, le=1, description="Sensitivity scale from 0 to 1")
    selected_products: List[str] = Field(description="List of selected reference products")

@router.get("/available-products")
async def get_available_products():
    """Get list of available reference products from database"""
    try:
        query = """
            SELECT DISTINCT product 
            FROM reference_data 
            WHERE product IS NOT NULL
            ORDER BY product
        """
        results = await db.execute_query(query)
        products = [result['product'] for result in results]
        
        if not products:
            products = ["No products available"]
            
        return {"products": products}
    except Exception as e:
        logger.error(f"Error getting available products: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/settings")
async def get_current_settings():
    """Get current model settings including sensitivity"""
    try:
        query = """
            SELECT 
                COALESCE(sensitivity, 0.5) as sensitivity,
                selected_products
            FROM model_settings
            ORDER BY created_at DESC
            LIMIT 1
        """
        result = await db.execute_query(query)
        
        if result:
            return {
                "sensitivity": result[0].get('sensitivity', 0.5),
                "selected_products": result[0].get('selected_products', [])
            }
        else:
            return {
                "sensitivity": 0.5,
                "selected_products": []
            }
    except Exception as e:
        logger.error(f"Error getting settings: {str(e)}")
        return {
            "sensitivity": 0.5,
            "selected_products": []
        }

@router.put("/settings")
async def update_settings(settings_data: UpdateSettingsRequest):
    """Update model settings with sensitivity scale"""
    try:
        query = """
            INSERT INTO model_settings (sensitivity, selected_products, created_at, updated_at)
            VALUES (:sensitivity, :selected_products, NOW(), NOW())
            ON CONFLICT (id) DO UPDATE 
            SET sensitivity = :sensitivity,
                selected_products = :selected_products,
                updated_at = NOW()
        """
        
        await db.execute_query(query, {
            'sensitivity': settings_data.sensitivity,
            'selected_products': settings_data.selected_products
        })
        
        return {
            "status": "updated",
            "sensitivity": settings_data.sensitivity,
            "selected_products": settings_data.selected_products
        }
    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/settings/validate")
async def validate_settings(settings_data: UpdateSettingsRequest):
    """Validate settings before applying"""
    try:
        if not 0 <= settings_data.sensitivity <= 1:
            return {"valid": False, "message": "Sensitivity must be between 0 and 1"}
        
        if not settings_data.selected_products:
            return {"valid": False, "message": "At least one product must be selected"}
        
        return {"valid": True, "message": "Settings are valid"}
    except Exception as e:
        return {"valid": False, "message": str(e)}