from fastapi import APIRouter, Body, HTTPException, UploadFile, File, Depends
from sqlalchemy.orm import Session
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
        db = DatabaseConnection()
        results = await db.get_reference_data_list()
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

@router.put("/reference/{reference_id}")
async def update_reference_data(
    reference_id: str,
    update_data: Dict,
):
    """Update reference data with training information"""
    try:
        # Build update query dynamically based on provided fields
        update_fields = []
        params = {"reference_id": reference_id}
        
        if "used_for_training" in update_data:
            update_fields.append("used_for_training = :used_for_training")
            params["used_for_training"] = update_data["used_for_training"]
        
        if "training_version" in update_data:
            update_fields.append("training_version = :training_version")
            params["training_version"] = update_data["training_version"]
        
        if "distribution_hash" in update_data:
            update_fields.append("distribution_hash = :distribution_hash")
            params["distribution_hash"] = update_data["distribution_hash"]
        
        if "quality_score" in update_data:
            update_fields.append("quality_score = :quality_score")
            params["quality_score"] = update_data["quality_score"]
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        
        # Add updated_at
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        
        query = f"""
            UPDATE reference_data 
            SET {', '.join(update_fields)}
            WHERE reference_id = :reference_id
            RETURNING reference_id
        """
        
        result = db.execute(query, params)
        updated = result.fetchone()
        
        if not updated:
            raise HTTPException(status_code=404, detail="Reference data not found")
        
        db.commit()
        
        return {
            "status": "success",
            "reference_id": reference_id,
            "updated_fields": list(update_data.keys())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating reference data: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))