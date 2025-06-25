# backend/api/routes/training_routes.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import datetime
import numpy as np
from scipy import stats
import pickle
import os
import uuid

from backend.models import training_models
from backend.schemas import training_schemas
from backend.services import training_service

from backend.db.database import DatabaseConnection
db = DatabaseConnection()

router = APIRouter(prefix="/api", tags=["training"])

@router.get("/model-versions")
async def get_model_versions():
    """Get all available model versions"""
    try:
        versions = db.query(training_models.ModelVersion).order_by(
            training_models.ModelVersion.version_number.desc()
        ).all()
        
        return {
            "versions": [f"v{v.version_number}" for v in versions]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/model-metrics")
async def get_model_metrics(
    version: Optional[str] = Query(None)
):
    """Get metrics for a specific model version or latest"""
    try:
        version_number = int(version[1:]) if version else None
        
        query = db.query(training_models.VersionMetrics)
        
        if version_number:
            model_version = db.query(training_models.ModelVersion).filter(
                training_models.ModelVersion.version_number == version_number
            ).first()
            if model_version:
                query = query.filter(
                    training_models.VersionMetrics.model_version_id == model_version.id
                )
        
        metrics = query.order_by(
            training_models.VersionMetrics.created_at.desc()
        ).limit(50).all()
        
        return {
            "metrics": [
                {
                    "accuracy": m.accuracy,
                    "confidence": m.confidence,
                    "error_rate": m.error_rate,
                    "vamos_score": m.vamos_score,
                    "model_version": f"v{m.model_version.version_number}",
                    "created_at": m.created_at.isoformat(),
                    "status": m.model_version.status
                }
                for m in metrics
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/model-versions/comparison")
async def get_version_comparison():
    """Get comparison data across all model versions"""
    try:
        versions = db.query(training_models.ModelVersion).all()
        
        comparison_data = []
        for version in versions:
            latest_metrics = db.query(training_models.VersionMetrics).filter(
                training_models.VersionMetrics.model_version_id == version.id
            ).order_by(
                training_models.VersionMetrics.created_at.desc()
            ).first()
            
            if latest_metrics:
                comparison_data.append({
                    "version": f"v{version.version_number}",
                    "created_at": version.created_at.isoformat(),
                    "accuracy": latest_metrics.accuracy * 100,
                    "confidence": latest_metrics.confidence * 100,
                    "error_rate": latest_metrics.error_rate * 100,
                    "training_info": f"{version.training_data_ref}"
                })
        
        return {"comparison_data": comparison_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/training-history")
async def get_training_history():
    """Get model training history"""
    try:
        events = db.query(training_models.TrainingEvent).order_by(
            training_models.TrainingEvent.timestamp.desc()
        ).limit(100).all()
        
        history = []
        for event in events:
            history.append({
                "timestamp": event.timestamp.isoformat(),
                "version": f"v{event.model_version.version_number}",
                "event_type": event.event_type,
                "details": {
                    "confidence": event.confidence_score,
                    "insertion": event.matched_insertion,
                    "product": event.matched_product,
                    "duration": event.training_duration,
                    "accuracy": event.final_accuracy,
                    "status": event.status,
                    "user": event.initiated_by
                }
            })
        
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compare-distributions")
async def compare_distributions(
    request: training_schemas.DistributionComparisonRequest):
    """Compare distributions between new data and reference"""
    try:
        comparison_service = training_service.DistributionComparisonService()
        
        # Get reference data
        reference_data = db.query(training_models.ReferenceData).filter(
            training_models.ReferenceData.id == request.reference_id
        ).first()
        
        if not reference_data:
            raise HTTPException(status_code=404, detail="Reference data not found")
        
        # Calculate confidence and match score
        confidence = comparison_service.calculate_confidence(
            request.new_data,
            reference_data.data
        )
        
        match_score = comparison_service.calculate_match_score(
            request.new_data,
            reference_data
        )
        
        return {
            "confidence": confidence,
            "match_score": match_score,
            "reference_info": {
                "product": reference_data.product,
                "lot": reference_data.lot,
                "insertion": reference_data.insertion
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/retrain-model")
async def retrain_model(
    request: training_schemas.RetrainModelRequest):
    """Trigger model retraining with specific data"""
    try:
        # Create new model version
        current_version = db.query(training_models.ModelVersion).order_by(
            training_models.ModelVersion.version_number.desc()
        ).first()
        
        new_version_number = (current_version.version_number + 1) if current_version else 1
        
        new_version = training_models.ModelVersion(
            id=str(uuid.uuid4()),
            version_number=new_version_number,
            created_at=datetime.utcnow(),
            parent_version=current_version.id if current_version else None,
            training_data_ref=request.training_data.get('reference_id'),
            confidence_score=request.training_data.get('confidence', 0),
            status="training"
        )
        db.add(new_version)
        
        # Log training event
        training_event = training_models.TrainingEvent(
            id=str(uuid.uuid4()),
            model_version_id=new_version.id,
            timestamp=datetime.utcnow(),
            event_type="AUTOMATIC_RETRAIN" if request.training_data.get('automatic') else "MANUAL_RETRAIN",
            confidence_score=request.training_data.get('confidence', 0),
            matched_insertion=request.training_data.get('insertion'),
            matched_product=request.training_data.get('product'),
            initiated_by=request.training_data.get('user', 'VAMOS'),
            status="in_progress"
        )
        db.add(training_event)
        db.commit()
        
        # Trigger actual training (async task)
        model_training_service = training_service.ModelTrainingService()
        training_result = await model_training_service.train_model(
            new_version.id,
            request.training_data
        )
        
        # Update status
        new_version.status = "active"
        training_event.status = "completed"
        training_event.training_duration = training_result.get('duration')
        training_event.final_accuracy = training_result.get('accuracy')
        db.commit()
        
        return {
            "version": f"v{new_version_number}",
            "status": "completed",
            "metrics": training_result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/model-metrics/{version}")
async def update_model_metrics(
    version: str,
    request: training_schemas.UpdateMetricsRequest):
    """Update metrics for a model version"""
    try:
        version_number = int(version[1:])
        
        model_version = db.query(training_models.ModelVersion).filter(
            training_models.ModelVersion.version_number == version_number
        ).first()
        
        if not model_version:
            raise HTTPException(status_code=404, detail="Model version not found")
        
        # Add new metrics entry
        new_metrics = training_models.VersionMetrics(
            id=str(uuid.uuid4()),
            model_version_id=model_version.id,
            accuracy=request.metrics.get('accuracy', 0),
            confidence=request.metrics.get('confidence', 0),
            error_rate=request.metrics.get('error_rate', 0),
            vamos_score=request.metrics.get('vamos_score', 0),
            created_at=datetime.utcnow()
        )
        db.add(new_metrics)
        db.commit()
        
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/model-versions")
async def create_model_version(
    request: training_schemas.CreateVersionRequest):
    """Create a new model version entry"""
    try:
        new_version = training_models.ModelVersion(
            id=str(uuid.uuid4()),
            version_number=request.version_number,
            created_at=datetime.utcnow(),
            parent_version=request.parent_version,
            training_data_ref=request.training_data_ref,
            confidence_score=request.confidence_score,
            status=request.status or "active"
        )
        db.add(new_version)
        db.commit()
        
        return {
            "id": new_version.id,
            "version": f"v{new_version.version_number}",
            "status": new_version.status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/vamos-analysis/{reference_id}")
async def get_vamos_analysis(
    reference_id: str):
    """Get VAMOS analysis results for reference data"""
    try:
        analysis = db.query(training_models.VamosAnalysis).filter(
            training_models.VamosAnalysis.reference_id == reference_id
        ).first()
        
        if not analysis:
            return {"status": "no_analysis"}
        
        return {
            "reference_id": analysis.reference_id,
            "distribution_score": analysis.distribution_score,
            "confidence_level": analysis.confidence_level,
            "matched_patterns": analysis.matched_patterns,
            "recommendations": analysis.recommendations,
            "analyzed_at": analysis.analyzed_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/training-events")
async def log_training_event(
    request: training_schemas.TrainingEventRequest):
    """Log a training event"""
    try:
        event = training_models.TrainingEvent(
            id=str(uuid.uuid4()),
            model_version_id=request.model_version_id,
            timestamp=datetime.utcnow(),
            event_type=request.event_type,
            confidence_score=request.confidence_score,
            matched_insertion=request.matched_insertion,
            matched_product=request.matched_product,
            training_duration=request.training_duration,
            final_accuracy=request.final_accuracy,
            status=request.status,
            initiated_by=request.initiated_by
        )
        db.add(event)
        db.commit()
        
        return {"success": True, "event_id": event.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))