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

# Alembic migration script
"""
alembic revision --autogenerate -m "Add VAMOS tables for model versioning"

# Generated migration file content:
"""

# migrations/versions/xxxx_add_vamos_tables.py

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Create model_versions table
    op.create_table('model_versions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('parent_version', sa.String(), nullable=True),
        sa.Column('training_data_ref', sa.String(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('model_path', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['parent_version'], ['model_versions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version_number')
    )
    
    # Create version_metrics table
    op.create_table('version_metrics',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('model_version_id', sa.String(), nullable=False),
        sa.Column('accuracy', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('error_rate', sa.Float(), nullable=False),
        sa.Column('vamos_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('precision', sa.Float(), nullable=True),
        sa.Column('recall', sa.Float(), nullable=True),
        sa.Column('f1_score', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['model_version_id'], ['model_versions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create training_events table
    op.create_table('training_events',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('model_version_id', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('matched_insertion', sa.String(), nullable=True),
        sa.Column('matched_product', sa.String(), nullable=True),
        sa.Column('training_duration', sa.String(), nullable=True),
        sa.Column('final_accuracy', sa.Float(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('initiated_by', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['model_version_id'], ['model_versions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create vamos_analysis table
    op.create_table('vamos_analysis',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('reference_id', sa.String(), nullable=False),
        sa.Column('distribution_score', sa.Float(), nullable=False),
        sa.Column('confidence_level', sa.Float(), nullable=False),
        sa.Column('matched_patterns', sa.JSON(), nullable=True),
        sa.Column('recommendations', sa.JSON(), nullable=True),
        sa.Column('analyzed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add VAMOS fields to existing reference_data table
    op.add_column('reference_data', sa.Column('used_for_training', sa.Boolean(), nullable=True))
    op.add_column('reference_data', sa.Column('training_version', sa.String(), nullable=True))
    op.add_column('reference_data', sa.Column('distribution_hash', sa.String(), nullable=True))
    op.add_column('reference_data', sa.Column('quality_score', sa.Float(), nullable=True))
    
    # Create indexes for better performance
    op.create_index('idx_model_versions_status', 'model_versions', ['status'])
    op.create_index('idx_version_metrics_created', 'version_metrics', ['created_at'])
    op.create_index('idx_training_events_timestamp', 'training_events', ['timestamp'])
    op.create_index('idx_reference_data_insertion', 'reference_data', ['insertion'])
    op.create_index('idx_reference_data_product', 'reference_data', ['product'])

def downgrade():
    op.drop_index('idx_reference_data_product')
    op.drop_index('idx_reference_data_insertion')
    op.drop_index('idx_training_events_timestamp')
    op.drop_index('idx_version_metrics_created')
    op.drop_index('idx_model_versions_status')
    
    op.drop_column('reference_data', 'quality_score')
    op.drop_column('reference_data', 'distribution_hash')
    op.drop_column('reference_data', 'training_version')
    op.drop_column('reference_data', 'used_for_training')
    
    op.drop_table('vamos_analysis')
    op.drop_table('training_events')
    op.drop_table('version_metrics')
    op.drop_table('model_versions')