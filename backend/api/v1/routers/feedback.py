from fastapi import APIRouter, HTTPException, Query, Path, Depends
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from backend.db.database import DatabaseConnection
from backend.core.config import get_settings
from pydantic import BaseModel, Field, ValidationError

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()
db = DatabaseConnection()
settings = get_settings()

from enum import Enum
from pydantic import BaseModel, Field

class SeverityLevel(str, Enum):
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    MEDIUM = "MEDIUM"

class FeedbackData(BaseModel):
    severity: SeverityLevel = Field(..., description="Severity level (HIGH, CRITICAL, MEDIUM)")
    test_name: str
    test_number: str
    lot: str
    insertion: str
    initial_label: str
    new_label: Optional[str] = None
    reference_id: str
    input_id: str

@router.get("/all")
async def get_all_feedback(
    limit: Optional[int] = Query(50, ge=1, le=100),
    offset: Optional[int] = Query(0, ge=0)
):
    """
    Get all feedback entries with optional pagination
    
    Args:
        limit (int, optional): Maximum number of feedback entries to return (default 50, max 100)
        offset (int, optional): Number of entries to skip for pagination (default 0)
    
    Returns:
        Dict containing list of all feedback entries
    """
    try:
        # Ensure limit and offset are integers
        limit = limit or 50
        offset = offset or 0
        
        query = """
            SELECT * FROM feedback
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """
        
        params = {
            'limit': limit,
            'offset': offset
        }
        
        results = await db.execute_query(query, params)
        
        # Log API request
        await db.log_api_request({
            'endpoint': '/feedback/all',
            'method': 'GET',
            'status_code': 200,
            'response_time': 0
        })
        
        return {
            "status": "success",
            "data": results,
            "total_count": len(results)
        }
    except Exception as e:
        logger.error(f"Error getting all feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/submit")
async def submit_feedback(
    feedback_data: FeedbackData,
):
    """
    Submit feedback for a distribution analysis
    """
    try:
        feedback_dict = feedback_data.model_dump()
        feedback_dict['status'] = 'PENDING'
        try:
            logger.info(f"Creating feedback: {feedback_dict}")
            feedback_id = await db.create_feedback(feedback_dict)
            logger.info(f"Feedback created successfully: {feedback_id}")
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Database error: {str(e)}"
            )

        # Log successful API request
        await db.log_api_request({
            'endpoint': '/feedback/submit',
            'method': 'POST',
            'status_code': 200,
            'response_time': 0
        })

        return {
            "status": "success",
            "feedback_id": feedback_id,
            "message": "Feedback submitted successfully"
        }

    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
        raise e
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{feedback_id}")
async def get_feedback(
    feedback_id: int = Path(..., description="The ID of the feedback to retrieve")
):
    """Get specific feedback entry"""
    try:
        feedback = await db.get_feedback(feedback_id)
        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")
        return feedback
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/pending")
async def get_pending_feedback(
    limit: int = Query(10, ge=1, le=100),
    severity: Optional[str] = Query(None, description="Filter by severity level")
):
    """Get all pending feedback"""
    try:
        query = """
            SELECT f.*, 
                   ar.distribution_type,
                   ar.confidence_score
            FROM feedback f
            LEFT JOIN analysis_results ar ON f.input_id = ar.input_id
            WHERE f.status = 'PENDING'
        """
        params = {'limit': limit}

        if severity:
            if severity not in settings.SEVERITY_LEVELS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid severity. Must be one of: {settings.SEVERITY_LEVELS}"
                )
            query += " AND f.severity = :severity"
            params['severity'] = severity

        query += " ORDER BY f.created_at DESC LIMIT :limit"
        
        results = await db.execute_query(query, params)
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pending feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{feedback_id}/status")
async def update_feedback_status(
    feedback_id: int = Path(..., description="The ID of the feedback to update"),
    status: str = Query(..., description="New status value")
):
    """Update feedback status"""
    try:
        if status not in settings.FEEDBACK_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {settings.FEEDBACK_STATUSES}"
            )

        success = await db.update_feedback_status(feedback_id, status)
        if not success:
            raise HTTPException(status_code=404, detail="Feedback not found")
        
        return {"status": "updated", "feedback_id": feedback_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating feedback status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search_feedback(
    test_name: Optional[str] = None,
    lot: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=100)
):
    """Search feedback with filters"""
    try:
        conditions = ["1=1"]
        params = {'limit': limit}
        
        if test_name:
            conditions.append("test_name LIKE :test_name")
            params['test_name'] = f"%{test_name}%"
        if lot:
            conditions.append("lot LIKE :lot")
            params['lot'] = f"%{lot}%"
        if severity:
            if severity not in settings.SEVERITY_LEVELS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid severity. Must be one of: {settings.SEVERITY_LEVELS}"
                )
            conditions.append("severity = :severity")
            params['severity'] = severity
        if status:
            if status not in settings.FEEDBACK_STATUSES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status. Must be one of: {settings.FEEDBACK_STATUSES}"
                )
            conditions.append("status = :status")
            params['status'] = status
        if start_date:
            conditions.append("created_at >= :start_date")
            params['start_date'] = start_date
        if end_date:
            conditions.append("created_at <= :end_date")
            params['end_date'] = end_date

        query = f"""
            SELECT 
                f.*,
                ar.distribution_type,
                ar.confidence_score
            FROM feedback f
            LEFT JOIN analysis_results ar ON f.input_id = ar.input_id
            WHERE {" AND ".join(conditions)}
            ORDER BY f.created_at DESC
            LIMIT :limit
        """
        
        results = await db.execute_query(query, params)
        return results
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))