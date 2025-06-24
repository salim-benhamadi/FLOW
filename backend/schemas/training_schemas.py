 
#backend/schemas/training_schemas.py

from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime

class DistributionComparisonRequest(BaseModel):
    new_data: Dict
    reference_id: str

class RetrainModelRequest(BaseModel):
    training_data: Dict

class UpdateMetricsRequest(BaseModel):
    metrics: Dict

class CreateVersionRequest(BaseModel):
    version_number: int
    parent_version: Optional[str]
    training_data_ref: Optional[str]
    confidence_score: Optional[float]
    status: Optional[str] = "active"

class TrainingEventRequest(BaseModel):
    model_version_id: str
    event_type: str
    confidence_score: Optional[float]
    matched_insertion: Optional[str]
    matched_product: Optional[str]
    training_duration: Optional[str]
    final_accuracy: Optional[float]
    status: str
    initiated_by: Optional[str]