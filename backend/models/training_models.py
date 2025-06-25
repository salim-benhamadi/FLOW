# backend/models/training_models.py

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class ModelVersion(Base):
    """Model version tracking table"""
    __tablename__ = "model_versions"
    
    id = Column(String, primary_key=True)
    version_number = Column(Integer, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    parent_version = Column(String, ForeignKey("model_versions.id"), nullable=True)
    training_data_ref = Column(String, nullable=True)  # Reference to training data used
    confidence_score = Column(Float, nullable=True)  # VAMOS confidence that triggered training
    status = Column(String, default="active")  # active, deprecated, training
    model_path = Column(String, nullable=True)  # Path to model file
    
    # Relationships
    metrics = relationship("VersionMetrics", back_populates="model_version")
    training_events = relationship("TrainingEvent", back_populates="model_version")
    parent = relationship("ModelVersion", remote_side=[id])

class VersionMetrics(Base):
    """Metrics for each model version"""
    __tablename__ = "version_metrics"
    
    id = Column(String, primary_key=True)
    model_version_id = Column(String, ForeignKey("model_versions.id"), nullable=False)
    accuracy = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    error_rate = Column(Float, nullable=False)
    vamos_score = Column(Float, nullable=True)  # Overall VAMOS quality score
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Additional metrics
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    
    # Relationships
    model_version = relationship("ModelVersion", back_populates="metrics")

class TrainingEvent(Base):
    """Training event history"""
    __tablename__ = "training_events"
    
    id = Column(String, primary_key=True)
    model_version_id = Column(String, ForeignKey("model_versions.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    event_type = Column(String, nullable=False)  # AUTOMATIC_RETRAIN, MANUAL_RETRAIN
    confidence_score = Column(Float, nullable=True)  # Confidence that triggered auto-retrain
    matched_insertion = Column(String, nullable=True)
    matched_product = Column(String, nullable=True)
    training_duration = Column(String, nullable=True)  # Duration as string (e.g., "5m 23s")
    final_accuracy = Column(Float, nullable=True)
    status = Column(String, nullable=False)  # in_progress, completed, failed
    initiated_by = Column(String, nullable=True)  # User or "VAMOS" for automatic
    error_message = Column(Text, nullable=True)
    
    # Relationships
    model_version = relationship("ModelVersion", back_populates="training_events")

class VamosAnalysis(Base):
    """VAMOS analysis results for reference data"""
    __tablename__ = "vamos_analysis"
    
    id = Column(String, primary_key=True)
    reference_id = Column(String, nullable=False)
    distribution_score = Column(Float, nullable=False)
    confidence_level = Column(Float, nullable=False)
    matched_patterns = Column(JSON, nullable=True)  # Patterns found in distribution
    recommendations = Column(JSON, nullable=True)  # Recommendations based on analysis
    analyzed_at = Column(DateTime, default=datetime.utcnow)

class ReferenceData(Base):
    """Enhanced reference data table with VAMOS fields"""
    __tablename__ = "reference_data"
    
    id = Column(String, primary_key=True)
    product = Column(String, nullable=False)
    lot = Column(String, nullable=False)
    insertion = Column(String, nullable=False)
    test_name = Column(String, nullable=True)
    data = Column(JSON, nullable=False)  # Actual test data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # VAMOS specific fields
    used_for_training = Column(Boolean, default=False)
    training_version = Column(String, nullable=True)  # Which model version used this data
    distribution_hash = Column(String, nullable=True)  # Hash of distribution for quick comparison
    quality_score = Column(Float, nullable=True)  # Data quality score