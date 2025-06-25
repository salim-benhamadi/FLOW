import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib
import logging
import os
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from scipy import stats
import re

# Import EFF utility
try:
    from ui.utils.Effio import EFF
except ImportError:
    from Effio import EFF

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DistributionSimilarityModel:
    """
    Model class for loading and using trained LightGBM distribution similarity model.
    Supports multiple model versions and sensitivity adjustments.
    """
    
    def __init__(self, model_path: str = None):
        """
        Initialize the model predictor.
        
        Args:
            model_path: Path to the trained model (optional)
        """
        self.model = None
        self.model_version = None
        self.model_loaded = False
        self.model_components = None
        self.model_base_path = Path("models")
        self.model_base_path.mkdir(parents=True, exist_ok=True)
        
        # Model components
        self.label_encoder = None
        self.feature_columns = []
        self.sensitivity_thresholds = {}
        self.label_mapping = {
            'Similar distribution': 0,
            'Moderately similar': 1, 
            'Completely different': 2
        }
        
        # Load model if path provided
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path: str = None, version: str = None) -> bool:
        """
        Load model by path or version
        
        Args:
            model_path: Direct path to model file
            version: Model version (e.g., 'v1', 'v2')
            
        Returns:
            Success status
        """
        try:
            if version:
                # Load by version
                model_path = self._get_model_path_by_version(version)
                self.model_version = version
            elif model_path:
                # Extract version from path if possible
                self.model_version = self._extract_version_from_path(model_path)
            else:
                # Load default/latest model
                model_path = self._get_latest_model_path()
                self.model_version = 'latest'
            
            if not os.path.exists(model_path):
                logger.error(f"Model file not found: {model_path}")
                return False
            
            # Load LightGBM model
            self.model = lgb.Booster(model_file=model_path)
            
            # Load associated components
            components_path = model_path.replace('.txt', '_components.pkl')
            if os.path.exists(components_path):
                self.model_components = joblib.load(components_path)
                self.feature_columns = self.model_components.get('feature_columns', [])
                self.sensitivity_thresholds = self.model_components.get('sensitivity_thresholds', {})
                self.label_encoder = self.model_components.get('label_encoder')
                self.label_mapping = self.model_components.get('label_mapping', self.label_mapping)
            else:
                logger.warning(f"Components file not found: {components_path}")
                # Initialize with defaults if components missing
                self._initialize_default_components()
            
            self.model_loaded = True
            logger.info(f"Model {self.model_version} loaded successfully from {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            self.model_loaded = False
            return False
    
    def _initialize_default_components(self):
        """Initialize default components when pkl file is missing"""
        # Default sensitivity thresholds
        self.sensitivity_thresholds = {
            0.0: 0.7, 0.1: 0.75, 0.2: 0.8, 0.3: 0.85,
            0.4: 0.87, 0.5: 0.9, 0.6: 0.92, 0.7: 0.94,
            0.8: 0.96, 0.9: 0.98, 1.0: 0.99
        }
        
        # Default feature columns (based on typical statistical features)
        self.feature_columns = [
            'mean_input', 'mean_reference', 'mean_diff', 'mean_ratio',
            'std_input', 'std_reference', 'std_diff', 'std_ratio',
            'min_input', 'min_reference', 'max_input', 'max_reference',
            'ks_statistic', 'ks_pvalue', 'iqr_ratio', 'cv_diff',
            'skew_diff', 'kurt_diff', 'range_ratio', 'n_ratio'
        ]
    
    def _get_model_path_by_version(self, version: str) -> str:
        """Get model file path for a specific version"""
        version_map = {
            'v1': 'my_distribution_model.txt',
        }
        
        filename = version_map.get(version, f'{version}.txt')
        return str(self.model_base_path / filename)
    
    def _get_latest_model_path(self) -> str:
        """Find the latest model version available"""
        model_files = list(self.model_base_path.glob('my_distribution_model*.txt'))
        
        if not model_files:
            return str(self.model_base_path / 'my_distribution_model.txt')
        
        # Sort by modification time to get the latest
        latest_file = max(model_files, key=lambda p: p.stat().st_mtime)
        return str(latest_file)
    
    def _extract_version_from_path(self, model_path: str) -> str:
        """Extract version from model file path"""
        match = re.search(r'my_distribution_model_v(\d+)', model_path)
        if match:
            return f'v{match.group(1)}'
        elif 'my_distribution_model.txt' in model_path:
            return 'v1'
        return 'unknown'
    
    def get_model_info(self) -> Dict:
        """Get information about the loaded model"""
        if not self.model_loaded:
            return {'status': 'not_loaded'}
        
        info = {
            'version': self.model_version,
            'loaded': self.model_loaded,
            'num_features': len(self.feature_columns) if self.feature_columns else 0,
            'feature_columns': self.feature_columns,
            'has_components': self.model_components is not None
        }
        
        if self.model:
            try:
                info['num_trees'] = self.model.num_trees()
                info['num_iterations'] = self.model.current_iteration()
            except:
                pass
        
        return info
    
    def download_and_load_model(self, version: str, api_client) -> bool:
        """
        Download a model version from cloud and load it
        
        Args:
            version: Model version to download
            api_client: API client instance for downloading
            
        Returns:
            Success status
        """
        try:
            model_path = self._get_model_path_by_version(version)
            
            # Check if already exists
            if os.path.exists(model_path):
                logger.info(f"Model {version} already exists locally")
                return self.load_model(version=version)
            
            # Download from cloud
            logger.info(f"Downloading model {version} from cloud...")
            
            loop = asyncio.get_event_loop()
            success = loop.run_until_complete(
                api_client.download_model(version, model_path)
            )
            
            if success:
                # Also download components if available
                components_path = model_path.replace('.txt', '_components.pkl')
                loop.run_until_complete(
                    api_client.download_model(f"{version}_components", components_path)
                )
                
                return self.load_model(version=version)
            else:
                logger.error(f"Failed to download model {version}")
                return False
                
        except Exception as e:
            logger.error(f"Error downloading model: {str(e)}")
            return False
    
    def extract_features(self, df_input: pd.DataFrame, df_reference: pd.DataFrame, 
                        selected_items: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Extract features from input and reference data.
        
        Args:
            df_input: Input EFF data
            df_reference: Reference EFF data  
            selected_items: List of test items to analyze. If None, uses all available tests.
            
        Returns:
            DataFrame with extracted features for ML model
        """
        features_list = []
        
        # Get selected items if not provided
        if selected_items is None:
            desc_rows = EFF.get_description_rows(df_input, header="<+ParameterName>")
            mask = desc_rows.loc['<+ParameterNumber>'].apply(lambda x: str(x).isdigit())
            selected_items = desc_rows.columns[mask].tolist()
        
        # Get test numbers
        desc_rows = EFF.get_description_rows(df_input, header="<+ParameterName>")
        
        for item in selected_items:
            if item not in desc_rows.columns:
                continue
                
            try:
                # Get test info
                test_number = str(desc_rows[item].loc['<+ParameterNumber>'])
                
                # Extract data
                input_data = df_input[item].dropna().values
                reference_data = df_reference[item].dropna().values if item in df_reference.columns else np.array([])
                
                if len(input_data) == 0 or len(reference_data) == 0:
                    continue
                
                # Calculate statistical features
                features = self._calculate_statistical_features(input_data, reference_data)
                features['test_name'] = item
                features['test_number'] = test_number
                
                features_list.append(features)
                
            except Exception as e:
                logger.warning(f"Error extracting features for {item}: {str(e)}")
                continue
        
        if not features_list:
            return pd.DataFrame()
        
        return pd.DataFrame(features_list)
    
    def _calculate_statistical_features(self, input_data: np.ndarray, reference_data: np.ndarray) -> Dict[str, float]:
        """
        Calculate statistical features for ML model.
        
        Args:
            input_data: Input data array
            reference_data: Reference data array
            
        Returns:
            Dictionary of features
        """
        try:
            # Basic statistics
            features = {
                'mean_input': np.mean(input_data),
                'mean_reference': np.mean(reference_data),
                'std_input': np.std(input_data, ddof=1),
                'std_reference': np.std(reference_data, ddof=1),
                'min_input': np.min(input_data),
                'min_reference': np.min(reference_data),
                'max_input': np.max(input_data),
                'max_reference': np.max(reference_data),
                'median_input': np.median(input_data),
                'median_reference': np.median(reference_data)
            }
            
            # Relative differences
            features['mean_diff'] = abs(features['mean_input'] - features['mean_reference'])
            features['mean_ratio'] = features['mean_input'] / (features['mean_reference'] + 1e-10)
            features['std_diff'] = abs(features['std_input'] - features['std_reference'])
            features['std_ratio'] = features['std_input'] / (features['std_reference'] + 1e-10)
            
            # Statistical tests
            ks_stat, ks_pval = stats.ks_2samp(input_data, reference_data)
            features['ks_statistic'] = ks_stat
            features['ks_pvalue'] = ks_pval
            
            # Percentiles
            for p in [1, 5, 25, 75, 95, 99]:
                features[f'p{p}_input'] = np.percentile(input_data, p)
                features[f'p{p}_reference'] = np.percentile(reference_data, p)
                features[f'p{p}_diff'] = abs(features[f'p{p}_input'] - features[f'p{p}_reference'])
                features[f'p{p}_diff_pct'] = features[f'p{p}_diff'] / (abs(features[f'p{p}_reference']) + 1e-10)
            
            # IQR
            features['iqr_input'] = features['p75_input'] - features['p25_input']
            features['iqr_reference'] = features['p75_reference'] - features['p25_reference']
            features['iqr_ratio'] = features['iqr_input'] / (features['iqr_reference'] + 1e-10)
            
            # Quartile differences
            features['q1_diff_pct'] = features.get('p25_diff_pct', 0)
            features['q3_diff_pct'] = features.get('p75_diff_pct', 0)
            features['iqr_overlap'] = min(features['p75_input'], features['p75_reference']) - max(features['p25_input'], features['p25_reference'])
            
            # Shape differences
            features['skew_input'] = stats.skew(input_data)
            features['skew_reference'] = stats.skew(reference_data)
            features['skew_diff'] = abs(features['skew_input'] - features['skew_reference'])
            
            features['kurt_input'] = stats.kurtosis(input_data)
            features['kurt_reference'] = stats.kurtosis(reference_data)
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
        feature_data = features[self.feature_columns] if self.feature_columns else features
        
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
        
        Args:
            df_input: Input EFF data
            df_reference: Reference EFF data
            selected_items: List of test items to analyze. If None, uses all available tests.
            sensitivity: Sensitivity level (0.0 to 1.0)
            
        Returns:
            DataFrame with analysis results
        """
        if not self.model_loaded:
            logger.warning("Model not loaded - falling back to rule-based analysis")
            return self._fallback_analysis(df_input, df_reference, selected_items, sensitivity)
        
        try:
            # Extract features
            features_df = self.extract_features(df_input, df_reference, selected_items)
            
            if features_df.empty:
                raise ValueError("No features could be extracted")
            
            # Make predictions
            predictions, confidence_scores = self.predict_with_sensitivity(features_df, sensitivity)
            
            # Convert predictions to labels
            label_mapping_inv = {v: k for k, v in self.label_mapping.items()}
            predicted_labels = [label_mapping_inv.get(pred, 'Unknown') for pred in predictions]
            
            # Create result DataFrame
            result_df = pd.DataFrame()
            
            # Get test numbers for index
            if selected_items is None:
                desc_rows = EFF.get_description_rows(df_input, header="<+ParameterName>")
                mask = desc_rows.loc['<+ParameterNumber>'].apply(lambda x: str(x).isdigit())
                selected_items = desc_rows.columns[mask].tolist()
            
            desc_rows = EFF.get_description_rows(df_input, header="<+ParameterName>")
            test_numbers = []
            for item in selected_items:
                if item in desc_rows.columns:
                    test_numbers.append(str(desc_rows[item].loc['<+ParameterNumber>']))
            
            result_df.index = test_numbers[:len(predicted_labels)]
            result_df['target'] = predicted_labels
            result_df['confidence_score'] = confidence_scores
            result_df['sensitivity_level'] = sensitivity
            result_df['ml_prediction'] = True
            result_df['model_version'] = self.model_version
            
            # Add statistical features for reference
            for i, (_, row) in enumerate(features_df.iterrows()):
                if i < len(result_df):
                    for col in ['mean_input', 'std_input', 'ks_statistic', 'ks_pvalue']:
                        if col in row:
                            result_df.iloc[i][col] = row[col]
            
            logger.info(f"ML analysis completed for {len(result_df)} tests using model {self.model_version}")
            logger.info(f"Prediction distribution: {pd.Series(predicted_labels).value_counts().to_dict()}")
            
            return result_df
            
        except Exception as e:
            logger.error(f"Error in ML analysis: {str(e)}")
            logger.warning("Falling back to rule-based analysis")
            return self._fallback_analysis(df_input, df_reference, selected_items, sensitivity)
    
    def _fallback_analysis(self, df_input: pd.DataFrame, df_reference: pd.DataFrame,
                          selected_items: Optional[List[str]], sensitivity: float) -> pd.DataFrame:
        """
        Fallback rule-based analysis when ML model is not available
        """
        try:
            # Extract features for rule-based analysis
            features_df = self.extract_features(df_input, df_reference, selected_items)
            
            if features_df.empty:
                return pd.DataFrame()
            
            # Rule-based classification
            predictions = []
            confidence_scores = []
            
            # Adjust thresholds based on sensitivity
            ks_threshold_similar = 0.1 + (0.2 * sensitivity)
            ks_threshold_different = 0.3 + (0.3 * sensitivity)
            mean_ratio_threshold = 0.1 + (0.15 * sensitivity)
            
            for _, row in features_df.iterrows():
                ks_stat = row.get('ks_statistic', 1.0)
                ks_pval = row.get('ks_pvalue', 0.0)
                mean_ratio = abs(1 - row.get('mean_ratio', 1.0))
                std_ratio = abs(1 - row.get('std_ratio', 1.0))
                
                # Rule-based decision
                if ks_stat < ks_threshold_similar and mean_ratio < mean_ratio_threshold:
                    prediction = 'Similar distribution'
                    confidence = 0.9 - ks_stat
                elif ks_stat > ks_threshold_different or mean_ratio > 0.5:
                    prediction = 'Completely different'
                    confidence = min(ks_stat, 0.95)
                else:
                    prediction = 'Moderately similar'
                    confidence = 0.7
                
                predictions.append(prediction)
                confidence_scores.append(confidence)
            
            # Create result DataFrame
            result_df = pd.DataFrame()
            
            # Get test numbers
            desc_rows = EFF.get_description_rows(df_input, header="<+ParameterName>")
            test_numbers = []
            for item in features_df['test_name']:
                if item in desc_rows.columns:
                    test_numbers.append(str(desc_rows[item].loc['<+ParameterNumber>']))
            
            result_df.index = test_numbers
            result_df['target'] = predictions
            result_df['confidence_score'] = confidence_scores
            result_df['sensitivity_level'] = sensitivity
            result_df['ml_prediction'] = False
            result_df['model_version'] = 'rule_based'
            
            logger.info(f"Rule-based analysis completed for {len(result_df)} tests")
            
            return result_df
            
        except Exception as e:
            logger.error(f"Error in fallback analysis: {str(e)}")
            return pd.DataFrame()


# Create a global instance for easy access
_model_instance = None

def get_model_instance(model_path: str = None) -> DistributionSimilarityModel:
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
                                  sensitivity: float = 0.5,
                                  model_version: str = None) -> pd.DataFrame:
    """
    Main function to analyze distribution similarity using ML model.
    
    Args:
        df_input: Input EFF data
        df_reference: Reference EFF data
        selected_items: List of test items to analyze. If None, uses all available tests.
        sensitivity: Sensitivity level (0.0 to 1.0)
        model_version: Specific model version to use (optional)
        
    Returns:
        DataFrame with analysis results
    """
    model = get_model_instance()
    
    # Load specific version if requested
    if model_version and model_version != model.model_version:
        model.load_model(version=model_version)
    
    return model.analyze_distribution_similarity(df_input, df_reference, selected_items, sensitivity)