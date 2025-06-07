from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List, Dict
import pandas as pd
import logging
from datetime import datetime
from backend.services.model_service import ModelService
from backend.db.database import DatabaseConnection
from backend.core.config import get_settings

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()
model_service = ModelService()
db = DatabaseConnection()
settings = get_settings()

@router.post("/distribution")
async def analyze_distribution(
    file: UploadFile = File(...),
    selected_items: List[str] = None
):
    """
    Analyze distribution from uploaded file and store results
    """
    start_time = datetime.now()
    
    try:
        # Log API request
        await db.log_api_request({
            'endpoint': '/distribution',
            'method': 'POST',
            'status_code': 200,  # Initial status
            'response_time': 0  # Will be updated
        })

        # Read file contents
        contents = await file.read()
        logger.info(f"Processing file: {file.filename}")

        # Get current model settings
        model_settings = await db.get_model_settings()
        if not model_settings:
            logger.warning("No model settings found, using defaults")
            model_settings = settings.DEFAULT_MODEL_SETTINGS

        # Process data and get predictions
        results = await model_service.analyze_distribution(contents, selected_items)

        # Prepare input data for storage
        input_data = {
            'input_id': f"{results['test_name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'insertion': results.get('insertion', 'default'),
            'test_name': results['test_name'],
            'test_number': results.get('test_number', '0'),
            'lsl': results.get('lsl', 0),
            'usl': results.get('usl', 0)
        }

        # Prepare measurements data
        measurements = [
            {'chip_number': i, 'value': val}
            for i, val in enumerate(results.get('measurements', []), 1)
        ]

        # Save input data and measurements
        if not await db.save_input_data(input_data, measurements):
            logger.error("Failed to save input data")

        # Save analysis results
        analysis_data = {
            'test_name': results['test_name'],
            'distribution_type': results['predicted_distribution'],
            'confidence_score': results['confidence'],
            'model_version_id': model_service.get_model_version(),
            'input_id': input_data['input_id'],
            'result_metadata': results
        }

        await db.execute_query("""
            INSERT INTO analysis_results 
            (test_name, distribution_type, confidence_score, model_version_id, input_id, result_metadata)
            VALUES 
            (:test_name, :distribution_type, :confidence_score, :model_version_id, :input_id, :result_metadata::jsonb)
        """, analysis_data)

        # Update API log with actual response time
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        await db.execute_query("""
            UPDATE api_logs 
            SET response_time = :response_time 
            WHERE endpoint = '/distribution' 
            AND created_at = :created_at
        """, {
            'response_time': response_time,
            'created_at': start_time
        })

        return {
            **results,
            'analysis_id': input_data['input_id'],
            'processing_time_ms': response_time
        }

    except Exception as e:
        # Log the error
        logger.error(f"Error in analyze_distribution: {str(e)}")
        
        # Update API log with error status
        await db.log_api_request({
            'endpoint': '/distribution',
            'method': 'POST',
            'status_code': 500,
            'response_time': (datetime.now() - start_time).total_seconds() * 1000
        })
        
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analysis/{analysis_id}")
async def get_analysis_result(analysis_id: str):
    """
    Retrieve a specific analysis result
    """
    try:
        result = await db.execute_query("""
            SELECT * FROM analysis_results 
            WHERE input_id = :analysis_id
        """, {'analysis_id': analysis_id})
        
        if not result:
            raise HTTPException(status_code=404, detail="Analysis result not found")
            
        return result[0]
        
    except Exception as e:
        logger.error(f"Error retrieving analysis result: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analysis/recent")
async def get_recent_analyses(limit: int = 10):
    """
    Get recent analysis results
    """
    try:
        results = await db.execute_query("""
            SELECT 
                ar.test_name,
                ar.distribution_type,
                ar.confidence_score,
                ar.created_at,
                ar.result_metadata
            FROM analysis_results ar
            ORDER BY ar.created_at DESC
            LIMIT :limit
        """, {'limit': limit})
        
        return results
        
    except Exception as e:
        logger.error(f"Error retrieving recent analyses: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analyze/comparison/{input_id}")
async def compare_distributions(
    input_id: str,
    reference_id: str
):
    """Compare two distributions"""
    try:
        # Get both distributions' data
        input_data = await db.get_input_data_with_measurements(input_id)
        reference_data = await db.get_input_data_with_measurements(reference_id)
        
        if not input_data or not reference_data:
            raise HTTPException(status_code=404, detail="Data not found")

        # Perform comparison analysis
        comparison_result = await model_service.compare_distributions(
            input_data['measurements'],
            reference_data['measurements']
        )

        # Save comparison result
        await db.execute_query("""
            INSERT INTO analysis_results (
                test_name,
                distribution_type,
                confidence_score,
                model_version_id,
                input_id,
                result_metadata
            ) VALUES (
                :test_name,
                'comparison',
                :confidence_score,
                :model_version_id,
                :input_id,
                :result_metadata
            )
        """, {
            'test_name': f"comparison_{input_id}_{reference_id}",
            'confidence_score': comparison_result['confidence'],
            'model_version_id': model_service.get_model_version(),
            'input_id': input_id,
            'result_metadata': comparison_result
        })

        return comparison_result
    except Exception as e:
        logger.error(f"Error in distribution comparison: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))