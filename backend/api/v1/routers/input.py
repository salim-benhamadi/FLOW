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
async def upload_input_data(file: UploadFile = File(...)):
    """Upload and process input data file"""
    try:
        contents = await file.read()
        df = pd.read_csv(contents)
        
        # Process data and insert into database
        for _, row in df.iterrows():
            input_data = {
                'insertion': row['insertion'],
                'test_name': row['test_name'],
                'test_number': row['test_number'],
                'lsl': float(row.get('lsl', 0)) if not pd.isna(row.get('lsl')) else None,
                'usl': float(row.get('usl', 0)) if not pd.isna(row.get('usl')) else None,
                'created_at': datetime.now()
            }
            
            # Generate input_id
            input_id = f"INP_{row['test_name']}_{row['test_number']}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            input_data['input_id'] = input_id
            
            # Insert input data
            await db.execute_query("""
                INSERT INTO input_data 
                (input_id, insertion, test_name, test_number, lsl, usl, created_at)
                VALUES 
                (:input_id, :insertion, :test_name, :test_number, :lsl, :usl, :created_at)
            """, input_data)
            
            # Insert measurements
            if 'measurements' in row:
                measurements = [{'input_id': input_id, 'chip_number': i+1, 'value': val} 
                              for i, val in enumerate(str(row['measurements']).split(','))]
                
                await db.execute_query("""
                    INSERT INTO input_measurements 
                    (input_id, chip_number, value)
                    VALUES 
                    (:input_id, :chip_number, :value)
                """, measurements)
            
        return {"status": "success", "message": "Input data uploaded successfully"}
        
    except Exception as e:
        logger.error(f"Error uploading input data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list")
async def list_input_data():
    """Get list of all input data"""
    try:
        query = """
            SELECT 
                input_id,
                insertion,
                test_name,
                test_number,
                CAST(lsl AS FLOAT) as lsl,
                CAST(usl AS FLOAT) as usl,
                created_at::timestamp
            FROM input_data
            ORDER BY created_at DESC
        """
        results = await db.execute_query(query)
        return results
    except Exception as e:
        logger.error(f"Error listing input data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{input_id}")
async def get_input_data(input_id: str):
    """Get specific input data entry with measurements"""
    try:
        query = """
            SELECT 
                i.*,
                array_agg(im.value ORDER BY im.chip_number) as measurements
            FROM input_data i
            LEFT JOIN input_measurements im ON i.input_id = im.input_id
            WHERE i.input_id = :input_id
            GROUP BY i.input_id, i.insertion, i.test_name, 
                     i.test_number, i.lsl, i.usl, i.created_at
        """
        result = await db.execute_query(query, {'input_id': input_id})
        
        if not result:
            raise HTTPException(status_code=404, detail="Input data not found")
            
        return result[0]
    except Exception as e:
        logger.error(f"Error getting input data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{input_id}")
async def delete_input_data(input_id: str):
    """Delete input data entry and its measurements"""
    try:
        # Delete measurements first due to foreign key constraint
        await db.execute_query("""
            DELETE FROM input_measurements 
            WHERE input_id = :input_id
        """, {'input_id': input_id})
        
        # Then delete input data
        result = await db.execute_query("""
            DELETE FROM input_data 
            WHERE input_id = :input_id
            RETURNING input_id
        """, {'input_id': input_id})
        
        if not result:
            raise HTTPException(status_code=404, detail="Input data not found")
            
        return {"status": "success", "message": "Input data deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting input data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save")
async def save_input_data(data: Dict = Body(...)):
    """Save input data and measurements"""
    try:
        logger.info(f"Attempting to save input data: {data['input_id']}")
        
        
        input_data = {
            'input_id': data['input_id'],
            'insertion': data['insertion'],
            'test_name': data['test_name'],
            'test_number': data['test_number'],
            'lsl': data.get('lsl'),
            'usl': data.get('usl')
        }
                
        measurements = []
        if 'measurements' in data:
            measurements = [
                {
                    'chip_number': m['chip_number'],
                    'value': m['value']
                }
                for m in data['measurements']
            ]

        success = await db.save_input_data(input_data, measurements)
        
        if success:
            logger.info(f"Successfully saved input data: {data['input_id']}")
        else:
            logger.error(f"Failed to save input data: {data['input_id']}")
            raise HTTPException(status_code=500, detail="Failed to save input data")

        return {
            'status': 'success',
            'input_id': data['input_id']
        }

    except Exception as e:
        logger.error(f"Error saving input data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{input_id}/measurements")
async def get_input_measurements(input_id: str):
    """Get measurements for specific input data entry"""
    try:
        query = """
            SELECT chip_number, value
            FROM input_measurements
            WHERE input_id = :input_id
            ORDER BY chip_number
        """
        results = await db.execute_query(query, {'input_id': input_id})
        
        if not results:
            raise HTTPException(status_code=404, detail="No measurements found for this input")
            
        return results
    except Exception as e:
        logger.error(f"Error getting input measurements: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))