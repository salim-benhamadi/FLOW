from fastapi import APIRouter, Body, HTTPException, UploadFile, File
from typing import List, Dict
import pandas as pd
import logging
from datetime import datetime
from backend.db.database import DatabaseConnection
from backend.core.config import get_settings

router = APIRouter()
db = DatabaseConnection()
logger = logging.getLogger(__name__)

@router.post("/upload")
async def upload_reference_data(file: UploadFile = File(...)):
    """Upload and process reference data file"""
    try:
        contents = await file.read()
        df = pd.read_csv(contents)
        
        # Process data and insert into database
        for _, row in df.iterrows():
            reference_data = {
                'product': row['product'],
                'lot': row['lot'],
                'insertion': row['insertion'],
                'test_name': row['test_name'],
                'test_number': row['test_number'],
                'lsl': float(row['lsl']),
                'usl': float(row['usl']),
                'created_at': datetime.now()
            }
            
            # Generate reference_id
            reference_id = f"REF_{row['product']}_{row['lot']}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            reference_data['reference_id'] = reference_id
            
            # Insert reference data
            await db.execute_query("""
                INSERT INTO reference_data 
                (reference_id, product, lot, insertion, test_name, test_number, lsl, usl, created_at)
                VALUES 
                (:reference_id, :product, :lot, :insertion, :test_name, :test_number, :lsl, :usl, :created_at)
            """, reference_data)
            
            # Insert measurements
            measurements = [{'reference_id': reference_id, 'chip_number': i+1, 'value': val} 
                          for i, val in enumerate(row['measurements'].split(','))]
            
            await db.execute_query("""
                INSERT INTO reference_measurements 
                (reference_id, chip_number, value)
                VALUES 
                (:reference_id, :chip_number, :value)
            """, measurements)
            
        return {"status": "success", "message": "Reference data uploaded successfully"}
        
    except Exception as e:
        logger.error(f"Error uploading reference data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_reference_data():
    """Get list of all reference data"""
    try:
        logger.debug("Starting reference data fetch")
        db = DatabaseConnection()
        results = await db.get_reference_data_list()
        logger.debug(f"Got {len(results)} reference data entries")
        logger.debug(f"First result (if any): {results[0] if results else None}")
        return results
    except Exception as e:
        logger.error(f"Error listing reference data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{reference_id}")
async def get_reference_data(reference_id: str):
    """Get specific reference data entry"""
    try:
        result = await db.execute_query("""
            SELECT 
                r.*,
                array_agg(rm.value ORDER BY rm.chip_number) as measurements
            FROM reference_data r
            LEFT JOIN reference_measurements rm ON r.reference_id = rm.reference_id
            WHERE r.reference_id = :reference_id
            GROUP BY r.reference_id, r.product, r.lot, r.insertion, r.test_name, 
                     r.test_number, r.lsl, r.usl, r.created_at
        """, {'reference_id': reference_id})
        
        if not result:
            raise HTTPException(status_code=404, detail="Reference data not found")
            
        return result[0]
    except Exception as e:
        logger.error(f"Error getting reference data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{reference_id}")
async def delete_reference_data(reference_id: str):
    """Delete reference data entry"""
    try:
        # Delete measurements first due to foreign key constraint
        await db.execute_query("""
            DELETE FROM reference_measurements 
            WHERE reference_id = :reference_id
        """, {'reference_id': reference_id})
        
        # Then delete reference data
        result = await db.execute_query("""
            DELETE FROM reference_data 
            WHERE reference_id = :reference_id
            RETURNING reference_id
        """, {'reference_id': reference_id})
        
        if not result:
            raise HTTPException(status_code=404, detail="Reference data not found")
            
        return {"status": "success", "message": "Reference data deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting reference data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/save")
async def save_reference_data(data: Dict = Body(...)):
    """Save reference data and measurements"""
    try:
        logger.info(f"Attempting to save reference data: {data['reference_id']}")
        
        reference_data = {
            'reference_id': data['reference_id'],
            'product': data['product'],
            'lot': data['lot'],
            'insertion': data['insertion'],
            'test_name': data['test_name'],
            'test_number': data['test_number'],
            'lsl': data['lsl'],
            'usl': data['usl']
        }
        
        logger.debug(f"Processed reference data: {reference_data}")
        logger.debug(f"Number of measurements: {len(data['measurements'])}")
        
        measurements = [
            {
                'chip_number': m['chip_number'],
                'value': m['value']
            }
            for m in data['measurements']
        ]

        success = await db.save_reference_data(reference_data, measurements)
        
        if success:
            logger.info(f"Successfully saved reference data: {data['reference_id']}")
        else:
            logger.error(f"Failed to save reference data: {data['reference_id']}")
            raise HTTPException(status_code=500, detail="Failed to save reference data")

        return {
            'status': 'success',
            'reference_id': data['reference_id']
        }

    except Exception as e:
        logger.error(f"Error saving reference data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))