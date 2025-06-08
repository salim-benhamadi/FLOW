import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
import lightgbm as lgb
import os
import logging
from backend.db.database import DatabaseConnection
from backend.core.config import get_settings
from backend.services.effio_service import EFF

# Set up logging
logger = logging.getLogger(__name__)

class ModelService:
    def __init__(self):
        self.settings = get_settings()
        self.db = DatabaseConnection()
        self.model = self._load_model()
        
    def _load_model(self) -> Optional[lgb.Booster]:
        """Load the LightGBM model with robust error handling"""
        try:
            model_path = self.settings.MODEL_PATH
            
            # Check if model file exists
            if not os.path.exists(model_path):
                logger.warning(f"Model file not found at: {model_path}")
                logger.info("Application will run without ML model - distribution analysis will use statistical methods")
                return None
            
            # Check if file is readable
            if not os.access(model_path, os.R_OK):
                logger.error(f"Model file exists but is not readable: {model_path}")
                return None
            
            # Try to load the model
            model = lgb.Booster(model_file=model_path)
            logger.info(f"Model loaded successfully from: {model_path}")
            return model
            
        except Exception as e:
            logger.error(f"Failed to load model from {self.settings.MODEL_PATH}: {str(e)}")
            logger.info("Application will continue without ML model")
            return None
    
    def _load_reference_data(self) -> Optional[pd.DataFrame]:
        """Load reference data with error handling"""
        try:
            reference_path = self.settings.REFERENCE_DATA_PATH
            
            if not os.path.exists(reference_path):
                logger.warning(f"Reference data file not found at: {reference_path}")
                return None
            
            df_reference, _ = EFF.read(reference_path)
            logger.info(f"Reference data loaded successfully from: {reference_path}")
            return df_reference
            
        except Exception as e:
            logger.error(f"Failed to load reference data: {str(e)}")
            return None
    
    async def analyze_distribution(self, file_contents: bytes, selected_items: List[str]) -> Dict[str, Any]:
        """Analyze distribution similarity with fallback methods"""
        try:
            # Save temporary file
            temp_file = 'temp.eff'
            with open(temp_file, 'wb') as f:
                f.write(file_contents)
            
            # Read input EFF file
            df_input, _ = EFF.read(temp_file)
            
            # Load reference data
            df_reference = self._load_reference_data()
            if df_reference is None:
                logger.warning("No reference data available - using input data statistics only")
                return self._analyze_input_only(df_input, selected_items)
            
            # Process data
            results = self._process_data(df_input, df_reference, selected_items)
            
            # Get predictions (with fallback)
            predictions = self._get_predictions(results)
            
            return {
                "results": results.to_dict(orient='records'),
                "predictions": predictions.tolist() if predictions is not None else [],
                "model_available": self.model is not None,
                "reference_data_available": df_reference is not None
            }
            
        except Exception as e:
            logger.error(f"Error in distribution analysis: {str(e)}")
            raise Exception(f"Error in distribution analysis: {str(e)}")
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    logger.warning(f"Could not remove temporary file {temp_file}: {e}")
    
    def _analyze_input_only(self, df_input: pd.DataFrame, selected_items: List[str]) -> Dict[str, Any]:
        """Fallback analysis using only input data statistics"""
        try:
            # Basic statistical analysis
            stats = {}
            for item in selected_items:
                if item in df_input.columns:
                    stats[item] = {
                        'mean': float(df_input[item].mean()) if pd.api.types.is_numeric_dtype(df_input[item]) else None,
                        'std': float(df_input[item].std()) if pd.api.types.is_numeric_dtype(df_input[item]) else None,
                        'count': int(df_input[item].count()),
                        'null_count': int(df_input[item].isnull().sum())
                    }
            
            return {
                "results": [stats],
                "predictions": [],
                "model_available": False,
                "reference_data_available": False,
                "analysis_type": "statistical_only"
            }
        except Exception as e:
            logger.error(f"Error in fallback analysis: {str(e)}")
            return {
                "results": [],
                "predictions": [],
                "model_available": False,
                "reference_data_available": False,
                "error": "Analysis failed"
            }
    
    def _process_data(self, df_input: pd.DataFrame, df_reference: pd.DataFrame, 
                     selected_items: List[str]) -> pd.DataFrame:
        """Process input data and calculate features"""
        try:
            # Your existing data processing logic here
            # For now, return a simple processed dataframe
            processed_data = pd.DataFrame()
            
            for item in selected_items:
                if item in df_input.columns and item in df_reference.columns:
                    # Simple feature extraction example
                    input_mean = df_input[item].mean() if pd.api.types.is_numeric_dtype(df_input[item]) else 0
                    ref_mean = df_reference[item].mean() if pd.api.types.is_numeric_dtype(df_reference[item]) else 0
                    
                    processed_data = pd.concat([processed_data, pd.DataFrame({
                        'item': [item],
                        'input_mean': [input_mean],
                        'reference_mean': [ref_mean],
                        'difference': [abs(input_mean - ref_mean)]
                    })], ignore_index=True)
            
            return processed_data
        except Exception as e:
            logger.error(f"Error in data processing: {str(e)}")
            return pd.DataFrame()
    
    def _get_predictions(self, processed_data: pd.DataFrame) -> Optional[np.ndarray]:
        """Get model predictions with fallback"""
        try:
            if self.model is None:
                logger.warning("No model available for predictions")
                return None
            
            if processed_data.empty:
                logger.warning("No processed data available for predictions")
                return None
            
            # Extract features for prediction
            features = self._extract_features(processed_data)
            if features is None:
                return None
            
            predictions = self.model.predict(features)
            return predictions
            
        except Exception as e:
            logger.error(f"Error getting predictions: {str(e)}")
            return None
    
    def _extract_features(self, processed_data: pd.DataFrame) -> Optional[np.ndarray]:
        """Extract features for model prediction"""
        try:
            if processed_data.empty:
                return None
            
            # Simple feature extraction - adjust based on your model's expected input
            numeric_columns = processed_data.select_dtypes(include=[np.number]).columns
            if len(numeric_columns) == 0:
                logger.warning("No numeric features found for prediction")
                return None
            
            features = processed_data[numeric_columns].values
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features: {str(e)}")
            return None
    
    async def retrain_model(self, feedback_data: pd.DataFrame):
        """Retrain model with new feedback data"""
        try:
            if self.model is None:
                logger.warning("Cannot retrain - no base model available")
                return {"status": "error", "message": "No base model available for retraining"}
            
            # Get training data
            training_data = self._prepare_training_data(feedback_data)
            if training_data is None or training_data.empty:
                return {"status": "error", "message": "No valid training data available"}
            
            # Train new model
            new_model = self._train_model(training_data)
            if new_model is None:
                return {"status": "error", "message": "Model training failed"}
            
            # Try to save model
            try:
                # Ensure directory exists
                model_dir = os.path.dirname(self.settings.MODEL_PATH)
                os.makedirs(model_dir, exist_ok=True)
                
                new_model.save_model(self.settings.MODEL_PATH)
                logger.info(f"Model saved successfully to: {self.settings.MODEL_PATH}")
            except Exception as e:
                logger.error(f"Failed to save model: {str(e)}")
                # Continue anyway - we can still use the model in memory
            
            # Update model instance
            self.model = new_model
            
            return {"status": "success", "message": "Model retrained successfully"}
            
        except Exception as e:
            logger.error(f"Error in model retraining: {str(e)}")
            return {"status": "error", "message": f"Model retraining failed: {str(e)}"}
    
    def _prepare_training_data(self, feedback_data: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Prepare data for model training"""
        try:
            # Add your training data preparation logic here
            # For now, return the feedback data as-is
            return feedback_data if not feedback_data.empty else None
        except Exception as e:
            logger.error(f"Error preparing training data: {str(e)}")
            return None
    
    def _train_model(self, training_data: pd.DataFrame) -> Optional[lgb.Booster]:
        """Train LightGBM model"""
        try:
            # Add your model training logic here
            # This is a placeholder implementation
            logger.info("Training new model...")
            
            # Example basic training setup
            # You'll need to implement this based on your specific requirements
            
            return None  # Replace with actual trained model
            
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            return None
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for the model service"""
        return {
            "model_loaded": self.model is not None,
            "model_path": self.settings.MODEL_PATH,
            "model_path_exists": os.path.exists(self.settings.MODEL_PATH),
            "reference_data_path": self.settings.REFERENCE_DATA_PATH,
            "reference_data_exists": os.path.exists(self.settings.REFERENCE_DATA_PATH),
            "database_connection": self.db is not None
        }