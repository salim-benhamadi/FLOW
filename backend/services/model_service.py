import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
import lightgbm as lgb
import os
import logging
import re
from backend.db.database import DatabaseConnection
from backend.core.config import get_settings
from backend.services.effio_service import EFF

logger = logging.getLogger(__name__)

class ModelService:
    def __init__(self):
        self.settings = get_settings()
        self.db = DatabaseConnection()
        self.current_version = None
        self.model = None
        self._initialize_model()
        
    def _initialize_model(self):
        """Initialize model with version support"""
        try:
            # Get active model version from settings
            settings = self._get_active_settings()
            if settings and 'model_version' in settings:
                self.current_version = settings['model_version']
                self.model = self._load_model(self.current_version)
            else:
                # Load latest version
                self.model = self._load_latest_model()
        except Exception as e:
            logger.error(f"Error initializing model: {e}")
            self.model = None
    
    def _get_active_settings(self) -> Optional[Dict]:
        """Get active model settings from database"""
        try:
            query = """
                SELECT model_version, sensitivity, auto_update
                FROM model_settings
                ORDER BY created_at DESC
                LIMIT 1
            """
            result = self.db.execute_query_sync(query)
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting settings: {e}")
            return None
    
    def _load_model(self, version: Optional[str] = None) -> Optional[lgb.Booster]:
        """Load the LightGBM model with version support"""
        try:
            if version and version != 'v1':
                # Load specific version
                model_path = f"{self.settings.MODEL_PATH.replace('.pkl', '')}_{version}.pkl"
            else:
                # Load base model
                model_path = self.settings.MODEL_PATH
            
            # Check if model file exists
            if not os.path.exists(model_path):
                logger.warning(f"Model file not found at: {model_path}")
                return None
            
            # Check if file is readable
            if not os.access(model_path, os.R_OK):
                logger.error(f"Model file exists but is not readable: {model_path}")
                return None
            
            # Try to load the model
            model = lgb.Booster(model_file=model_path)
            logger.info(f"Model loaded successfully from: {model_path} (version: {version or 'v1'})")
            self.current_version = version or 'v1'
            return model
            
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            return None
    
    def _load_latest_model(self) -> Optional[lgb.Booster]:
        """Load the latest available model version"""
        try:
            # Find all model files
            model_dir = os.path.dirname(self.settings.MODEL_PATH)
            model_base = os.path.basename(self.settings.MODEL_PATH).replace('.pkl', '')
            
            if not os.path.exists(model_dir):
                return None
            
            # Find version files
            version_pattern = re.compile(f"{model_base}_v(\\d+)\\.pkl")
            versions = []
            
            for filename in os.listdir(model_dir):
                match = version_pattern.match(filename)
                if match:
                    versions.append(int(match.group(1)))
            
            if versions:
                # Load highest version
                latest_version = max(versions)
                return self._load_model(f"v{latest_version}")
            else:
                # Load base model
                return self._load_model()
                
        except Exception as e:
            logger.error(f"Error finding latest model: {e}")
            return None
    
    def reload_model(self, version: Optional[str] = None):
        """Reload model with specific version"""
        if version:
            self.model = self._load_model(version)
        else:
            self._initialize_model()
    
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
                "model_version": self.current_version,
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
                "model_version": None,
                "reference_data_available": False,
                "analysis_type": "statistical_only"
            }
        except Exception as e:
            logger.error(f"Error in fallback analysis: {str(e)}")
            return {
                "results": [],
                "predictions": [],
                "model_available": False,
                "model_version": None,
                "reference_data_available": False,
                "error": str(e)
            }
    
    def _process_data(self, df_input: pd.DataFrame, df_reference: pd.DataFrame, 
                     selected_items: List[str]) -> pd.DataFrame:
        """Process input data and calculate features"""
        try:
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
            
            # Calculate new version number
            current_num = int(self.current_version[1:]) if self.current_version and self.current_version.startswith('v') else 1
            new_version = f"v{current_num + 1}"
            
            # Save new model version
            try:
                # Ensure directory exists
                model_dir = os.path.dirname(self.settings.MODEL_PATH)
                os.makedirs(model_dir, exist_ok=True)
                
                # Save with version
                model_path = f"{self.settings.MODEL_PATH.replace('.pkl', '')}_{new_version}.pkl"
                new_model.save_model(model_path)
                logger.info(f"Model saved successfully to: {model_path}")
                
                # Update current model
                self.model = new_model
                self.current_version = new_version
                
            except Exception as e:
                logger.error(f"Failed to save model: {str(e)}")
                return {"status": "error", "message": f"Failed to save model: {str(e)}"}
            
            return {
                "status": "success", 
                "message": "Model retrained successfully",
                "version": new_version
            }
            
        except Exception as e:
            logger.error(f"Error in model retraining: {str(e)}")
            return {"status": "error", "message": f"Model retraining failed: {str(e)}"}
    
    def _prepare_training_data(self, feedback_data: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Prepare data for model training"""
        try:
            # Add your training data preparation logic here
            return feedback_data if not feedback_data.empty else None
        except Exception as e:
            logger.error(f"Error preparing training data: {str(e)}")
            return None
    
    def _train_model(self, training_data: pd.DataFrame) -> Optional[lgb.Booster]:
        """Train LightGBM model"""
        try:
            # This is a placeholder - implement your actual training logic
            logger.info("Training new model...")
            
            # Example: create a simple model
            # You should replace this with your actual training code
            params = {
                'objective': 'regression',
                'metric': 'rmse',
                'boosting_type': 'gbdt',
                'num_leaves': 31,
                'learning_rate': 0.05,
                'feature_fraction': 0.9
            }
            
            # Placeholder for actual training
            # train_data = lgb.Dataset(X_train, label=y_train)
            # model = lgb.train(params, train_data, num_boost_round=100)
            
            return None  # Replace with actual trained model
            
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            return None
    
    def get_model_version(self) -> str:
        """Get current model version"""
        return self.current_version or 'v1'
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for the model service"""
        return {
            "model_loaded": self.model is not None,
            "model_version": self.current_version,
            "model_path": self.settings.MODEL_PATH,
            "model_path_exists": os.path.exists(self.settings.MODEL_PATH),
            "reference_data_path": self.settings.REFERENCE_DATA_PATH,
            "reference_data_exists": os.path.exists(self.settings.REFERENCE_DATA_PATH),
            "database_connection": self.db is not None
        }