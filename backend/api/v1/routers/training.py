# backend/api/v1/routers/training.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from typing import List, Dict, Optional
from datetime import datetime
import uuid
import logging

from backend.db.database import DatabaseConnection

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/model-versions")
async def get_model_versions():
    """Get all available model versions"""
    try:
        db = DatabaseConnection()
        
        # Use raw SQL instead of ORM
        query = """
        SELECT version_number 
        FROM model_versions 
        ORDER BY version_number DESC
        """
        
        with db.get_connection() as conn:
            result = conn.execute(text(query))
            versions = [f"v{row[0]}" for row in result]
            
            # If no versions exist, create default v1
            if not versions:
                create_query = """
                INSERT INTO model_versions (version_number, status, confidence_score)
                VALUES (1, 'active', 0.95)
                ON CONFLICT (version_number) DO NOTHING
                """
                conn.execute(text(create_query))
                conn.commit()
                versions = ['v1']
        
        return {"versions": versions}
        
    except Exception as e:
        logger.error(f"Error getting model versions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/model-metrics")
async def get_model_metrics(version: Optional[str] = Query(None)):
    """Get metrics for a specific model version or latest"""
    try:
        db = DatabaseConnection()
        
        if version:
            # Extract version number (remove 'v' prefix)
            version_number = int(version[1:]) if version.startswith('v') else int(version)
            
            query = """
            SELECT 
                vm.accuracy,
                vm.confidence, 
                vm.error_rate,
                vm.vamos_score,
                vm.created_at,
                mv.status,
                mv.version_number
            FROM version_metrics vm
            JOIN model_versions mv ON vm.model_version_id = mv.id
            WHERE mv.version_number = :version_number
            ORDER BY vm.created_at DESC
            LIMIT 50
            """
            params = {"version_number": version_number}
        else:
            query = """
            SELECT 
                vm.accuracy,
                vm.confidence,
                vm.error_rate, 
                vm.vamos_score,
                vm.created_at,
                mv.status,
                mv.version_number
            FROM version_metrics vm
            JOIN model_versions mv ON vm.model_version_id = mv.id
            ORDER BY vm.created_at DESC
            LIMIT 50
            """
            params = {}
        
        with db.get_connection() as conn:
            result = conn.execute(text(query), params)
            metrics = []
            
            for row in result:
                metrics.append({
                    "accuracy": float(row[0]) if row[0] else 0.0,
                    "confidence": float(row[1]) if row[1] else 0.0,
                    "error_rate": float(row[2]) if row[2] else 0.0,
                    "vamos_score": float(row[3]) if row[3] else 0.0,
                    "created_at": row[4].isoformat() if row[4] else "",
                    "status": row[5] or "active",
                    "model_version": f"v{row[6]}" if row[6] else "v1"
                })
        
        return {"metrics": metrics}
        
    except Exception as e:
        logger.error(f"Error getting model metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/model-versions/comparison")
async def get_version_comparison():
    """Get comparison data across all model versions"""
    try:
        db = DatabaseConnection()
        
        query = """
        SELECT DISTINCT
            mv.version_number,
            mv.created_at,
            mv.training_data_ref,
            vm.accuracy,
            vm.confidence,
            vm.error_rate
        FROM model_versions mv
        LEFT JOIN version_metrics vm ON mv.id = vm.model_version_id
        WHERE vm.id = (
            SELECT id FROM version_metrics vm2 
            WHERE vm2.model_version_id = mv.id 
            ORDER BY vm2.created_at DESC 
            LIMIT 1
        )
        ORDER BY mv.version_number DESC
        """
        
        with db.get_connection() as conn:
            result = conn.execute(text(query))
            comparison_data = []
            
            for row in result:
                comparison_data.append({
                    "version": f"v{row[0]}",
                    "created_at": row[1].isoformat() if row[1] else "",
                    "training_info": row[2] or "Initial version",
                    "accuracy": float(row[3] * 100) if row[3] else 0.0,
                    "confidence": float(row[4] * 100) if row[4] else 0.0,
                    "error_rate": float(row[5] * 100) if row[5] else 0.0
                })
        
        return {"comparison_data": comparison_data}
        
    except Exception as e:
        logger.error(f"Error getting version comparison: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/training-history")
async def get_training_history():
    """Get model training history"""
    try:
        db = DatabaseConnection()
        
        query = """
        SELECT 
            te.created_at,
            mv.version_number,
            te.event_type,
            te.matched_insertion,
            te.matched_product,
            te.training_duration,
            te.final_accuracy
        FROM training_events te
        JOIN model_versions mv ON te.model_version_id = mv.id
        ORDER BY te.created_at DESC
        LIMIT 100
        """
        
        with db.get_connection() as conn:
            result = conn.execute(text(query))
            history = []
            
            for row in result:
                history.append({
                    "timestamp": row[0].isoformat() if row[0] else "",
                    "version": f"v{row[1]}" if row[1] else "v1",
                    "event_type": row[2] or "UNKNOWN",
                    "details": {
                        "insertion": row[3],
                        "product": row[4], 
                        "duration": row[5],
                        "accuracy": float(row[6]) if row[6] else 0.0,
                        "status": "completed"
                    }
                })
        
        return {"history": history}
        
    except Exception as e:
        logger.error(f"Error getting training history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/model-versions")
async def create_model_version(version_data: Dict):
    """Create a new model version entry"""
    try:
        db = DatabaseConnection()
        
        query = """
        INSERT INTO model_versions (
            version_number, status, confidence_score, model_path, created_at
        ) VALUES (
            :version_number, :status, :confidence_score, :model_path, :created_at
        ) RETURNING id
        """
        
        params = {
            "version_number": version_data.get("version_number", 1),
            "status": version_data.get("status", "active"),
            "confidence_score": version_data.get("confidence_score", 0.95),
            "model_path": version_data.get("model_path"),
            "created_at": datetime.utcnow()
        }
        
        with db.get_connection() as conn:
            result = conn.execute(text(query), params)
            version_id = result.scalar()
            conn.commit()
        
        return {
            "id": version_id,
            "version": f"v{params['version_number']}",
            "status": params["status"]
        }
        
    except Exception as e:
        logger.error(f"Error creating model version: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.put("/model-metrics/{version}")
async def update_model_metrics(version: str, metrics_data: Dict):
    """Update metrics for a model version"""
    try:
        db = DatabaseConnection()
        version_number = int(version[1:]) if version.startswith('v') else int(version)
        
        # First, get the model version ID
        get_version_query = """
        SELECT id FROM model_versions WHERE version_number = :version_number
        """
        
        with db.get_connection() as conn:
            result = conn.execute(text(get_version_query), {"version_number": version_number})
            version_row = result.fetchone()
            
            if not version_row:
                raise HTTPException(status_code=404, detail="Model version not found")
            
            model_version_id = version_row[0]
            
            # Insert new metrics
            insert_query = """
            INSERT INTO version_metrics (
                model_version_id, accuracy, confidence, error_rate, vamos_score, created_at
            ) VALUES (
                :model_version_id, :accuracy, :confidence, :error_rate, :vamos_score, :created_at
            )
            """
            
            params = {
                "model_version_id": model_version_id,
                "accuracy": metrics_data.get("accuracy", 0.0),
                "confidence": metrics_data.get("confidence", 0.0), 
                "error_rate": metrics_data.get("error_rate", 0.0),
                "vamos_score": metrics_data.get("vamos_score", 0.0),
                "created_at": datetime.utcnow()
            }
            
            conn.execute(text(insert_query), params)
            conn.commit()
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Error updating model metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")