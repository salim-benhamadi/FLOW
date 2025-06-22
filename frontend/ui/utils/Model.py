import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from ui.utils.Effio import EFF

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DistributionSimilarityModel:
    """
    Model class for loading and using trained LightGBM distribution similarity model.
    This replaces the analyze_distribution_similarity function.
    """
    
    def __init__(self, model_path: str = "models/vamos_distribution_model"):
        """
        Initialize the model predictor.
        
        Args:
            model_path: Path to the trained model (without extension)
        """
        self.model_path = model_path
        self.model = None
        self.label_encoder = None
        self.feature_columns = []
        self.sensitivity_thresholds = {}
        self.model_loaded = False
        
        # Try to load the model
        self._load_model()
    
    def _load_model(self):
        """Load the trained model and associated components."""
        try:
            model_file = f"{self.model_path}.txt"
            components_file = f"{self.model_path}_components.pkl"
            
            if not Path(model_file).exists() or not Path(components_file).exists():
                logger.error(f"Model files not found: {self.model_path}")
                return
            
            # Load LightGBM model
            self.model = lgb.Booster(model_file=model_file)
            
            # Load components
            components = joblib.load(components_file)
            self.label_encoder = components['label_encoder']
            self.feature_columns = components['feature_columns']
            self.sensitivity_thresholds = components['sensitivity_thresholds']
            
            self.model_loaded = True
            logger.info(f"Model loaded successfully from {self.model_path}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            self.model_loaded = False
    
    def extract_features(self, df_input: pd.DataFrame, df_reference: pd.DataFrame, 
                        selected_items: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Extract features from input and reference data.
        
        Args:
            df_input: Input EFF data
            df_reference: Reference EFF data  
            selected_items: List of test items to analyze. If None, uses all available tests.
            
        Returns:
            DataFrame with extracted features
        """
        try:
            # If no specific items selected, use all available tests
            if selected_items is None:
                desc_rows = EFF.get_description_rows(df_input, header="<+ParameterName>")
                mask = desc_rows.loc['<+ParameterNumber>'].apply(lambda x: str(x).isdigit())
                selected_items = desc_rows.columns[mask].tolist()
                logger.info(f"Using all {len(selected_items)} available tests")
            
            # Get test numbers
            desc_rows = EFF.get_description_rows(df_input, header="<+ParameterName>")
            TNUMBERS = desc_rows[selected_items].loc['<+ParameterNumber>'].astype(str)
            
            # Get test data
            df_testdata_input = EFF.get_value_rows(df_input, header='<+ParameterNumber>', fix_dtypes=True)
            df_testdata_reference = EFF.get_value_rows(df_reference, header='<+ParameterNumber>', fix_dtypes=True)
            
            # Convert columns to string for consistency
            df_testdata_input.columns = df_testdata_input.columns.astype(str)
            df_testdata_reference.columns = df_testdata_reference.columns.astype(str)
            
            # Prepare data for analysis
            features_list = []
            
            for idx, t_number in enumerate(TNUMBERS):
                test_name = selected_items[idx]
                
                if t_number not in df_testdata_input.columns or t_number not in df_testdata_reference.columns:
                    logger.warning(f"Test number {t_number} not found in data columns")
                    continue
                
                # Get cleaned data
                input_series = df_testdata_input[t_number].dropna()
                reference_series = df_testdata_reference[t_number].dropna()
                
                if len(input_series) == 0 or len(reference_series) == 0:
                    logger.warning(f"No valid data for test {test_name}")
                    continue
                
                # Calculate features
                features = self._calculate_statistical_features(input_series, reference_series)
                features['test_name'] = test_name
                features['test_number'] = int(float(t_number))
                
                features_list.append(features)
            
            if not features_list:
                logger.error("No features extracted")
                return pd.DataFrame()
                
            logger.info(f"Extracted features for {len(features_list)} tests")
            return pd.DataFrame(features_list)
            
        except Exception as e:
            logger.error(f"Error extracting features: {str(e)}")
            return pd.DataFrame()
    
    def _calculate_statistical_features(self, input_data: pd.Series, reference_data: pd.Series) -> Dict[str, float]:
        """
        Calculate comprehensive statistical features.
        
        Args:
            input_data: Input measurements
            reference_data: Reference measurements
            
        Returns:
            Dictionary of calculated features
        """
        features = {}
        
        try:
            # Basic statistics
            features['mean_input'] = float(input_data.mean())
            features['mean_reference'] = float(reference_data.mean())
            features['std_input'] = float(input_data.std())
            features['std_reference'] = float(reference_data.std())
            features['min_input'] = float(input_data.min())
            features['min_reference'] = float(reference_data.min())
            features['max_input'] = float(input_data.max())
            features['max_reference'] = float(reference_data.max())
            features['median_input'] = float(input_data.median())
            features['median_reference'] = float(reference_data.median())
            
            # Percentiles
            for p in [1, 5, 25, 75, 95, 99]:
                features[f'p{p}_input'] = float(np.percentile(input_data, p))
                features[f'p{p}_reference'] = float(np.percentile(reference_data, p))
            
            # Advanced statistics
            features['skew_input'] = float(input_data.skew())
            features['skew_reference'] = float(reference_data.skew())
            features['kurt_input'] = float(input_data.kurtosis())
            features['kurt_reference'] = float(reference_data.kurtosis())
            
            # Relative differences (core features)
            features['mean_diff_abs'] = abs(features['mean_input'] - features['mean_reference'])
            features['std_diff_abs'] = abs(features['std_input'] - features['std_reference'])
            
            # Relative percentage differences
            mean_ref = abs(features['mean_reference']) + 1e-10
            std_ref = features['std_reference'] + 1e-10
            
            features['mean_diff_pct'] = (features['mean_diff_abs'] / mean_ref) * 100
            features['std_diff_pct'] = (features['std_diff_abs'] / std_ref) * 100
            
            # IQR calculations
            iqr_input = features['p75_input'] - features['p25_input']
            iqr_reference = features['p75_reference'] - features['p25_reference']
            
            features['iqr_input'] = iqr_input
            features['iqr_reference'] = iqr_reference
            features['iqr_diff'] = abs(iqr_input - iqr_reference)
            features['iqr_ratio'] = iqr_input / (iqr_reference + 1e-10)
            
            # RDRS and PRatio
            median_diff = abs(features['mean_input'] - features['mean_reference'])
            features['rdrs'] = median_diff / (iqr_reference + 1e-10)
            features['pratio'] = iqr_input / (iqr_reference + 1e-10)
            
            # Quartile differences
            q1_diff = abs(features['p25_input'] - features['p25_reference'])
            q3_diff = abs(features['p75_input'] - features['p75_reference'])
            
            features['q1_diff_pct'] = (q1_diff / (iqr_reference + 1e-10)) * 100
            features['q3_diff_pct'] = (q3_diff / (iqr_reference + 1e-10)) * 100
            features['quartile_diff'] = max(features['q1_diff_pct'], features['q3_diff_pct'])
            
            # Shape differences
            features['skew_diff'] = abs(features['skew_input'] - features['skew_reference'])
            features['kurt_diff'] = abs(features['kurt_input'] - features['kurt_reference'])
            
            # Range features
            range_input = features['max_input'] - features['min_input']
            range_reference = features['max_reference'] - features['min_reference']
            features['range_input'] = range_input
            features['range_reference'] = range_reference
            features['range_ratio'] = range_input / (range_reference + 1e-10)
            
            # Data quality features
            features['n_input'] = len(input_data)
            features['n_reference'] = len(reference_data)
            features['n_ratio'] = len(input_data) / (len(reference_data) + 1e-10)
            
            # Coefficient of variation
            features['cv_input'] = features['std_input'] / (abs(features['mean_input']) + 1e-10)
            features['cv_reference'] = features['std_reference'] / (abs(features['mean_reference']) + 1e-10)
            features['cv_diff'] = abs(features['cv_input'] - features['cv_reference'])
            
            return features
            
        except Exception as e:
            logger.error(f"Error calculating statistical features: {str(e)}")
            return {}
    
    def predict_with_sensitivity(self, features: pd.DataFrame, sensitivity: float = 0.5) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make predictions with adjustable sensitivity.
        
        Args:
            features: Feature matrix
            sensitivity: Sensitivity level (0.0 to 1.0)
            
        Returns:
            Tuple of (predictions, confidence_scores)
        """
        if not self.model_loaded:
            raise ValueError("Model not loaded")
        
        sensitivity = np.clip(sensitivity, 0.0, 1.0)
        sensitivity_key = round(sensitivity, 1)
        
        # Select only the features used during training
        feature_data = features[self.feature_columns]
        
        # Get predictions
        y_pred_proba = self.model.predict(feature_data, num_iteration=self.model.best_iteration)
        confidence_scores = np.max(y_pred_proba, axis=1)
        y_pred_classes = np.argmax(y_pred_proba, axis=1)
        
        # Apply sensitivity threshold
        if sensitivity_key in self.sensitivity_thresholds:
            threshold = self.sensitivity_thresholds[sensitivity_key]
            
            # For low confidence predictions, make them more conservative
            low_confidence_mask = confidence_scores < threshold
            
            if sensitivity < 0.5:
                # Low sensitivity: prefer "Similar distribution" for uncertain cases
                y_pred_classes[low_confidence_mask] = 0  # Similar distribution
            else:
                # High sensitivity: prefer "Completely different" for uncertain cases  
                y_pred_classes[low_confidence_mask] = 2  # Completely different
        
        return y_pred_classes, confidence_scores
    
    def analyze_distribution_similarity(self, df_input: pd.DataFrame, df_reference: pd.DataFrame, 
                                      selected_items: Optional[List[str]] = None, 
                                      sensitivity: float = 0.5) -> pd.DataFrame:
        """
        Main function to analyze distribution similarity using ML model.
        This replaces the original analyze_distribution_similarity function.
        
        Args:
            df_input: Input EFF data
            df_reference: Reference EFF data
            selected_items: List of test items to analyze. If None, uses all available tests.
            sensitivity: Sensitivity level (0.0 to 1.0)
            
        Returns:
            DataFrame with analysis results in the same format as the original function
        """
        if not self.model_loaded:
            raise ValueError("Model not loaded - cannot perform analysis")
        
        try:
            # Extract features
            features_df = self.extract_features(df_input, df_reference, selected_items)
            
            if features_df.empty:
                raise ValueError("No features could be extracted")
            
            # Make predictions
            predictions, confidence_scores = self.predict_with_sensitivity(features_df, sensitivity)
            
            # Convert predictions back to labels
            predicted_labels = self.label_encoder.inverse_transform(predictions)
            
            # Create result DataFrame compatible with original format
            result_df = pd.DataFrame()
            
            # Use test numbers as index for compatibility
            if selected_items is None:
                desc_rows = EFF.get_description_rows(df_input, header="<+ParameterName>")
                mask = desc_rows.loc['<+ParameterNumber>'].apply(lambda x: str(x).isdigit())
                selected_items = desc_rows.columns[mask].tolist()
            
            desc_rows = EFF.get_description_rows(df_input, header="<+ParameterName>")
            TNUMBERS = desc_rows[selected_items].loc['<+ParameterNumber>'].astype(str)
            
            result_df.index = TNUMBERS
            result_df['target'] = predicted_labels
            result_df['confidence_score'] = confidence_scores
            result_df['sensitivity_level'] = sensitivity
            result_df['ml_prediction'] = True
            
            # Add the statistical features for compatibility if needed
            for feature_name in ['mean_input', 'std_input', 'min_input', 'max_input']:
                if feature_name in features_df.columns:
                    result_df[feature_name] = features_df[feature_name].values
            
            # Add percentiles for compatibility
            for p in [1, 5, 25, 75, 95, 99]:
                for suffix in ['_input', '_reference']:
                    col_name = f'p{p}{suffix}'
                    if col_name in features_df.columns:
                        result_df[col_name] = features_df[col_name].values
            
            logger.info(f"ML analysis completed for {len(result_df)} tests")
            logger.info(f"Prediction distribution: {pd.Series(predicted_labels).value_counts().to_dict()}")
            
            return result_df
            
        except Exception as e:
            logger.error(f"Error in ML analysis: {str(e)}")
            raise


# Create a global instance for easy access
_model_instance = None

def get_model_instance(model_path: str = "models/vamos_distribution_model") -> DistributionSimilarityModel:
    """
    Get or create a global model instance.
    
    Args:
        model_path: Path to the trained model
        
    Returns:
        DistributionSimilarityModel instance
    """
    global _model_instance
    if _model_instance is None:
        _model_instance = DistributionSimilarityModel(model_path)
    return _model_instance

def analyze_distribution_similarity(df_input: pd.DataFrame, df_reference: pd.DataFrame, 
                                  selected_items: Optional[List[str]] = None, 
                                  sensitivity: float = 0.5) -> pd.DataFrame:
    """
    Main function to analyze distribution similarity using ML model.
    This function maintains the same interface as the original analyze_distribution_similarity.
    
    Args:
        df_input: Input EFF data
        df_reference: Reference EFF data
        selected_items: List of test items to analyze. If None, uses all available tests.
        sensitivity: Sensitivity level (0.0 to 1.0)
        
    Returns:
        DataFrame with analysis results
    """
    model = get_model_instance()
    return model.analyze_distribution_similarity(df_input, df_reference, selected_items, sensitivity)