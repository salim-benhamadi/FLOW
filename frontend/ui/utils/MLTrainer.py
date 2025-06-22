import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Any
import warnings
warnings.filterwarnings('ignore')

# Import your existing modules
from Effio import EFF
from Model import analyze_distribution_similarity

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DistributionSimilarityTrainer:
    """
    Machine Learning trainer for distribution similarity analysis using LightGBM.
    Uses the existing analyze_distribution_similarity function to generate labels.
    """
    
    def __init__(self, model_save_path: str = "models/"):
        """
        Initialize the trainer.
        
        Args:
            model_save_path: Directory to save trained models
        """
        self.model_save_path = Path(model_save_path)
        self.model_save_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.model = None
        self.label_encoder = LabelEncoder()
        self.feature_columns = []
        self.sensitivity_thresholds = {}
        
        # Label mapping from analyze_distribution_similarity
        self.label_mapping = {
            'Similar distribution': 0,
            'Moderately similar': 1, 
            'Completely different': 2
        }
        
        # Feature importance tracking
        self.feature_importance = None
        
    def extract_features(self, df_input: pd.DataFrame, df_reference: pd.DataFrame, 
                        selected_items: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Extract features from input and reference data for machine learning.
        
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
                # Get all test items that are numeric (have test numbers)
                desc_rows = EFF.get_description_rows(df_input, header="<+ParameterName>")
                mask = desc_rows.loc['<+ParameterNumber>'].apply(lambda x: str(x).isdigit())
                selected_items = desc_rows.columns[mask].tolist()
                logger.info(f"No tests specified, using all {len(selected_items)} available tests")
            
            # Get test numbers
            desc_rows = EFF.get_description_rows(df_input, header="<+ParameterName>")
            TNUMBERS = desc_rows[selected_items].loc['<+ParameterNumber>']
            TNUMBERS = TNUMBERS.astype(str)
            
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
        Calculate comprehensive statistical features for ML training.
        
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
            
            # RDRS and PRatio (from your existing implementation)
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
    
    def prepare_training_data(self, eff_file_pairs: List[Tuple[str, str]], 
                            selected_items: Optional[List[str]] = None) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare training data from EFF file pairs.
        
        Args:
            eff_file_pairs: List of (input_file, reference_file) tuples
            selected_items: List of test items to analyze. If None, uses all available tests.
            
        Returns:
            Tuple of (features_df, labels_series)
        """
        all_features = []
        all_labels = []
        
        logger.info(f"Processing {len(eff_file_pairs)} EFF file pairs...")
        
        for idx, (input_file, reference_file) in enumerate(eff_file_pairs):
            try:
                logger.info(f"Processing pair {idx + 1}/{len(eff_file_pairs)}: {Path(input_file).name}")
                
                # Read EFF files
                df_input, _ = EFF.read(input_file)
                df_reference, _ = EFF.read(reference_file)
                
                # Get selected items for this file pair if not specified
                current_selected_items = selected_items
                if current_selected_items is None:
                    # Get all available tests from the input file
                    desc_rows = EFF.get_description_rows(df_input, header="<+ParameterName>")
                    mask = desc_rows.loc['<+ParameterNumber>'].apply(lambda x: str(x).isdigit())
                    current_selected_items = desc_rows.columns[mask].tolist()
                    logger.info(f"Using {len(current_selected_items)} tests from file {Path(input_file).name}")
                
                # Extract features
                features_df = self.extract_features(df_input, df_reference, current_selected_items)
                
                if features_df.empty:
                    logger.warning(f"No features extracted from {input_file}")
                    continue
                
                # Generate labels using existing function
                labels_df = self._generate_labels_from_features(features_df)
                
                if labels_df.empty:
                    logger.warning(f"No labels generated from {input_file}")
                    continue
                
                # Merge features with labels
                combined_df = features_df.merge(labels_df[['test_name', 'target']], on='test_name', how='inner')
                
                if not combined_df.empty:
                    all_features.append(combined_df.drop(['target', 'test_name'], axis=1))
                    all_labels.extend(combined_df['target'].tolist())
                
            except Exception as e:
                logger.error(f"Error processing pair {input_file}, {reference_file}: {str(e)}")
                continue
        
        if not all_features:
            raise ValueError("No valid training data could be extracted from the provided EFF files")
        
        # Combine all features
        features_combined = pd.concat(all_features, ignore_index=True)
        labels_combined = pd.Series(all_labels)
        
        logger.info(f"Training data prepared: {len(features_combined)} samples, {len(features_combined.columns)} features")
        logger.info(f"Label distribution:\n{labels_combined.value_counts()}")
        
        return features_combined, labels_combined
    
    def _generate_labels_from_features(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate labels using the existing analyze_distribution_similarity function.
        
        Args:
            features_df: DataFrame with calculated features
            
        Returns:
            DataFrame with test names and labels
        """
        try:
            # Create a DataFrame in the format expected by analyze_distribution_similarity
            analysis_df = features_df.copy()
            
            # Use existing analysis function
            labeled_df = analyze_distribution_similarity(analysis_df)
            
            # Extract relevant columns
            result_df = pd.DataFrame({
                'test_name': features_df['test_name'],
                'target': labeled_df['target']
            })
            
            return result_df
            
        except Exception as e:
            logger.error(f"Error generating labels: {str(e)}")
            return pd.DataFrame()
    
    def train_model(self, features: pd.DataFrame, labels: pd.Series, 
                   test_size: float = 0.2, random_state: int = 42) -> Dict[str, Any]:
        """
        Train the LightGBM model.
        
        Args:
            features: Feature matrix
            labels: Target labels
            test_size: Proportion of data for testing
            random_state: Random seed for reproducibility
            
        Returns:
            Dictionary with training results
        """
        try:
            # Store feature columns
            self.feature_columns = features.columns.tolist()
            
            # Encode labels
            labels_encoded = self.label_encoder.fit_transform(labels)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                features, labels_encoded, test_size=test_size, 
                random_state=random_state, stratify=labels_encoded
            )
            
            # LightGBM parameters
            params = {
                'objective': 'multiclass',
                'num_class': len(self.label_encoder.classes_),
                'metric': 'multi_logloss',
                'boosting_type': 'gbdt',
                'num_leaves': 31,
                'learning_rate': 0.05,
                'feature_fraction': 0.9,
                'bagging_fraction': 0.8,
                'bagging_freq': 5,
                'verbose': -1,
                'random_state': random_state
            }
            
            # Create datasets
            train_data = lgb.Dataset(X_train, label=y_train)
            valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)
            
            # Train model
            logger.info("Training LightGBM model...")
            self.model = lgb.train(
                params,
                train_data,
                valid_sets=[train_data, valid_data],
                valid_names=['train', 'valid'],
                num_boost_round=1000,
                callbacks=[lgb.early_stopping(stopping_rounds=50), lgb.log_evaluation(0)]
            )
            
            # Make predictions
            y_pred = self.model.predict(X_test, num_iteration=self.model.best_iteration)
            y_pred_classes = np.argmax(y_pred, axis=1)
            
            # Calculate metrics
            accuracy = accuracy_score(y_test, y_pred_classes)
            
            # Feature importance
            self.feature_importance = pd.DataFrame({
                'feature': self.feature_columns,
                'importance': self.model.feature_importance(importance_type='gain')
            }).sort_values('importance', ascending=False)
            
            # Calculate sensitivity thresholds
            self._calculate_sensitivity_thresholds(X_test, y_pred)
            
            logger.info(f"Model trained successfully. Accuracy: {accuracy:.4f}")
            
            return {
                'accuracy': accuracy,
                'classification_report': classification_report(y_test, y_pred_classes, 
                                                             target_names=self.label_encoder.classes_),
                'confusion_matrix': confusion_matrix(y_test, y_pred_classes),
                'feature_importance': self.feature_importance,
                'label_mapping': dict(zip(self.label_encoder.classes_, self.label_encoder.transform(self.label_encoder.classes_)))
            }
            
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            raise
    
    def _calculate_sensitivity_thresholds(self, X_test: pd.DataFrame, y_pred_proba: np.ndarray):
        """
        Calculate probability thresholds for different sensitivity levels.
        
        Args:
            X_test: Test features
            y_pred_proba: Prediction probabilities
        """
        try:
            # Calculate confidence scores (max probability)
            confidence_scores = np.max(y_pred_proba, axis=1)
            
            # Calculate thresholds for sensitivity levels 0.0 to 1.0
            for sensitivity in np.arange(0.0, 1.1, 0.1):
                # Lower sensitivity = higher threshold (less sensitive to differences)
                # Higher sensitivity = lower threshold (more sensitive to differences)
                threshold = np.percentile(confidence_scores, (1 - sensitivity) * 100)
                self.sensitivity_thresholds[round(sensitivity, 1)] = threshold
            
            logger.info("Sensitivity thresholds calculated")
            
        except Exception as e:
            logger.error(f"Error calculating sensitivity thresholds: {str(e)}")
    
    def predict_with_sensitivity(self, features: pd.DataFrame, sensitivity: float = 0.5) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make predictions with adjustable sensitivity.
        
        Args:
            features: Feature matrix
            sensitivity: Sensitivity level (0.0 to 1.0)
            
        Returns:
            Tuple of (predictions, confidence_scores)
        """
        if self.model is None:
            raise ValueError("Model not trained yet")
        
        sensitivity = np.clip(sensitivity, 0.0, 1.0)
        sensitivity_key = round(sensitivity, 1)
        
        # Get predictions
        y_pred_proba = self.model.predict(features[self.feature_columns], num_iteration=self.model.best_iteration)
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
    
    def save_model(self, model_name: str = "distribution_similarity_model"):
        """
        Save the trained model and associated components.
        
        Args:
            model_name: Name for the saved model
        """
        if self.model is None:
            raise ValueError("No model to save")
        
        try:
            base_path = self.model_save_path / model_name
            
            # Save LightGBM model
            model_path = f"{base_path}.txt"
            self.model.save_model(model_path)
            
            # Save label encoder and other components
            components = {
                'label_encoder': self.label_encoder,
                'feature_columns': self.feature_columns,
                'sensitivity_thresholds': self.sensitivity_thresholds,
                'feature_importance': self.feature_importance,
                'label_mapping': self.label_mapping
            }
            
            joblib.dump(components, f"{base_path}_components.pkl")
            
            logger.info(f"Model saved successfully to {base_path}")
            
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
            raise
    
    def load_model(self, model_name: str = "distribution_similarity_model"):
        """
        Load a trained model and associated components.
        
        Args:
            model_name: Name of the model to load
        """
        try:
            base_path = self.model_save_path / model_name
            model_path = f"{base_path}.txt"
            components_path = f"{base_path}_components.pkl"
            
            if not Path(model_path).exists() or not Path(components_path).exists():
                raise FileNotFoundError(f"Model files not found: {base_path}")
            
            # Load LightGBM model
            self.model = lgb.Booster(model_file=model_path)
            
            # Load components
            components = joblib.load(components_path)
            self.label_encoder = components['label_encoder']
            self.feature_columns = components['feature_columns']
            self.sensitivity_thresholds = components['sensitivity_thresholds']
            self.feature_importance = components['feature_importance']
            self.label_mapping = components['label_mapping']
            
            logger.info(f"Model loaded successfully from {base_path}")
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise
    
    def analyze_with_model(self, input_file: str, reference_file: str, 
                          selected_items: Optional[List[str]] = None, sensitivity: float = 0.5) -> pd.DataFrame:
        """
        Analyze distribution similarity using the trained model.
        
        Args:
            input_file: Path to input EFF file
            reference_file: Path to reference EFF file
            selected_items: List of test items to analyze. If None, uses all available tests.
            sensitivity: Sensitivity level (0.0 to 1.0)
            
        Returns:
            DataFrame with analysis results
        """
        if self.model is None:
            raise ValueError("Model not loaded")
        
        try:
            # Read EFF files
            df_input, _ = EFF.read(input_file)
            df_reference, _ = EFF.read(reference_file)
            
            # Extract features
            features_df = self.extract_features(df_input, df_reference, selected_items)
            
            if features_df.empty:
                raise ValueError("No features could be extracted")
            
            # Make predictions
            predictions, confidence_scores = self.predict_with_sensitivity(features_df, sensitivity)
            
            # Convert predictions back to labels
            predicted_labels = self.label_encoder.inverse_transform(predictions)
            
            # Create results DataFrame
            results_df = features_df[['test_name', 'test_number']].copy()
            results_df['predicted_similarity'] = predicted_labels
            results_df['confidence_score'] = confidence_scores
            results_df['sensitivity_level'] = sensitivity
            
            return results_df
            
        except Exception as e:
            logger.error(f"Error analyzing with model: {str(e)}")
            raise


# Example usage function
def train_distribution_model_example():
    """
    Example function showing how to use the DistributionSimilarityTrainer.
    """
    # Initialize trainer
    trainer = DistributionSimilarityTrainer(model_save_path="models/")
    
    # Example EFF file pairs - replace with your actual file paths
    eff_file_pairs = [
        # B1 combinations
        ("resources/output/ZA407235G01_B1.eff", "resources/output/ZA407235G02_B1.eff"),
        ("resources/output/ZA407235G01_B1.eff", "resources/output/ZA407235G04_B1.eff"),
        ("resources/output/ZA407235G02_B1.eff", "resources/output/ZA407235G04_B1.eff"),
        
        # B2 combinations
        ("resources/output/ZA407235G01_B2.eff", "resources/output/ZA407235G02_B2.eff"),
        ("resources/output/ZA407235G01_B2.eff", "resources/output/ZA407235G04_B2.eff"),
        ("resources/output/ZA407235G01_B2.eff", "resources/output/ZA409123G02_B2.eff"),
        ("resources/output/ZA407235G01_B2.eff", "resources/output/ZA432191G09_B2.eff"),
        ("resources/output/ZA407235G02_B2.eff", "resources/output/ZA407235G04_B2.eff"),
        ("resources/output/ZA407235G02_B2.eff", "resources/output/ZA409123G02_B2.eff"),
        ("resources/output/ZA407235G02_B2.eff", "resources/output/ZA432191G09_B2.eff"),
        ("resources/output/ZA407235G04_B2.eff", "resources/output/ZA409123G02_B2.eff"),
        ("resources/output/ZA407235G04_B2.eff", "resources/output/ZA432191G09_B2.eff"),
        ("resources/output/ZA409123G02_B2.eff", "resources/output/ZA432191G09_B2.eff"),
        
        # B3 combinations
        ("resources/output/ZA407235G01_B3.eff", "resources/output/ZA407235G02_B3.eff"),
        ("resources/output/ZA407235G01_B3.eff", "resources/output/ZA407235G04_B3.eff"),
        ("resources/output/ZA407235G02_B3.eff", "resources/output/ZA407235G04_B3.eff"),
    ]
    
    # Train on all available tests (selected_items=None)
    try:
        # Prepare training data - will use all available tests
        features, labels = trainer.prepare_training_data(eff_file_pairs, selected_items=None)
        
        # Train model
        results = trainer.train_model(features, labels)
        
        print("Training Results:")
        print(f"Accuracy: {results['accuracy']:.4f}")
        print("\nFeature Importance (Top 10):")
        print(results['feature_importance'].head(10))
        
        # Save model
        trainer.save_model("my_distribution_model")
    
    except Exception as e:
        logger.error(f"Error in training example: {str(e)}")

if __name__ == "__main__":
    # Run example with all available tests
    train_distribution_model_example()