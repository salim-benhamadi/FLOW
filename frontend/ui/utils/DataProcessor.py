from PySide6.QtCore import Signal, QThread
from ui.utils.Model import analyze_distribution_similarity
from ui.utils.Effio import EFF
from api.reference_data_client import ReferenceDataClient
import pandas as pd
import numpy as np
import random
import re
import logging
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
from ui.utils.PathResources import resource_path
from scipy import stats

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataProcessor(QThread):
    progress = Signal(int)
    finished = Signal()
    result = Signal(object)
    error = Signal(str)
    file_processed = Signal(str, bool)
    def __init__(self, selected_items: Optional[List[str]] = None, files: List[str] = None, 
                 reference_config: Dict = None, sensitivity: float = 0.5, model_version: str = None):
        super().__init__()
        if not files:
            raise ValueError("Files cannot be empty")
        
        self.files = [str(Path(f).resolve()) for f in files]
        
        if selected_items:
            self.selected_items = [item.split(";")[1] for item in selected_items]
            self.selected_numbers = [item.split(";")[0] for item in selected_items]
            self.selected_names = [item.split(";")[1] for item in selected_items]
        else:
            self.selected_items = None
            self.selected_numbers = None
            self.selected_names = None
            
        self.sensitivity = np.clip(sensitivity, 0.0, 1.0)
        self.model_version = model_version
        self.results = []
        self._processed_count = 0
        
        # Store reference configuration
        self.reference_config = reference_config or {}
        self.reference_client = ReferenceDataClient()
        self.reference_data_cache = {}  # Cache for loaded reference data

    def set_sensitivity(self, sensitivity: float):
        self.sensitivity = np.clip(sensitivity, 0.0, 1.0)
    
    def _load_reference_data(self, insertion: str) -> List[Tuple[pd.DataFrame, Dict]]:
        """Load reference data based on configuration"""
        reference_data = []
        
        try:
            if self.reference_config.get("source") == "cloud":
                # Load from cloud
                cloud_selection = self.reference_config.get("cloud_selection", {})
                
                for product in cloud_selection.get("products", []):
                    if product in cloud_selection.get("lots", {}):
                        for insertion_name, lots in cloud_selection["lots"][product].items():
                            if insertion_name == insertion:  # Match insertion
                                for lot in lots:
                                    # Get reference data from cloud
                                    try:
                                        df_ref = self.reference_client.get_reference_data_by_criteria(
                                            product=product, 
                                            lot=lot, 
                                            insertion=insertion
                                        )
                                        if df_ref is not None and not df_ref.empty:
                                            metadata = {
                                                'product': product,
                                                'lot': lot,
                                                'insertion': insertion,
                                                'source': 'cloud'
                                            }
                                            reference_data.append((df_ref, metadata))
                                    except Exception as e:
                                        logger.warning(f"Failed to load cloud reference data for {product}-{lot}-{insertion}: {e}")
                
            else:
                # Load from local files
                reference_files = self.reference_config.get("files", [])
                
                for ref_file in reference_files:
                    try:
                        # Check cache first
                        if ref_file in self.reference_data_cache:
                            df_ref, ref_metadata = self.reference_data_cache[ref_file]
                        else:
                            df_ref, _ = EFF.read(ref_file)
                            df_info = EFF.get_value_rows(df_ref, header='<+ParameterName>')
                            
                            ref_metadata = {
                                'product': "NA",  # Local files don't have product info
                                'lot': df_info['Lot'].iloc[0] if not df_info.empty else "Unknown",
                                'insertion': df_info['MeasStep'].iloc[0] if not df_info.empty else "Unknown",
                                'source': 'local',
                                'file_path': ref_file
                            }
                            
                            # Cache the loaded data
                            self.reference_data_cache[ref_file] = (df_ref, ref_metadata)
                        
                        # Check if insertion matches
                        if ref_metadata['insertion'] == insertion:
                            reference_data.append((df_ref, ref_metadata))
                            
                    except Exception as e:
                        logger.warning(f"Failed to load local reference file {ref_file}: {e}")
        
        except Exception as e:
            logger.error(f"Error loading reference data: {e}")
        
        if not reference_data:
            logger.warning(f"No reference data found for insertion: {insertion}")
        else:
            logger.info(f"Loaded {len(reference_data)} reference datasets for insertion: {insertion}")
            
        return reference_data

    def _adjust_thresholds_by_sensitivity(self) -> dict:
        base_thresholds = {
            'cpk_threshold': 1.33,
            'yield_threshold': 0.95,
            'variance_threshold': 0.1,
            'outlier_threshold': 3.0
        }
        
        if self.sensitivity < 0.3:
            multiplier = 0.7
        elif self.sensitivity < 0.7:
            multiplier = 1.0
        else:
            multiplier = 1.3
        
        adjusted = {}
        for key, value in base_thresholds.items():
            if 'threshold' in key:
                if key in ['yield_threshold']:
                    adjusted[key] = value + (1 - value) * (1 - self.sensitivity) * 0.5
                else:
                    adjusted[key] = value * (2 - multiplier)
        
        return adjusted

    def _get_representative_sample(self, data: pd.DataFrame, n_samples: int = 201) -> np.ndarray:
        if data.empty or data.dropna().empty:
            return np.array([])
            
        total_rows = len(data)
        if total_rows <= n_samples:
            return np.arange(total_rows)
            
        valid_data = data.dropna()
        if len(valid_data) == 0:
            return np.array([])
            
        try:
            selected_indices = []
            for col in valid_data.columns:
                col_data = valid_data[col].values
                if len(col_data) == 0:
                    continue
                
                num_strata = min(20, len(col_data))
                strata_bounds = np.percentile(col_data, np.linspace(0, 100, num_strata))
                samples_per_stratum = max(1, n_samples // num_strata)
                
                for i in range(len(strata_bounds) - 1):
                    stratum_mask = (col_data >= strata_bounds[i]) & (col_data < strata_bounds[i + 1])
                    stratum_indices = np.where(stratum_mask)[0]
                    if len(stratum_indices) > 0:
                        selected = np.random.choice(stratum_indices, 
                                                  size=min(samples_per_stratum, len(stratum_indices)), 
                                                  replace=False)
                        selected_indices.extend(selected)
                        
            if not selected_indices:
                return np.random.choice(np.arange(len(valid_data)), 
                                      size=min(n_samples, len(valid_data)), 
                                      replace=False)
                                      
            unique_indices = np.unique(selected_indices)
            if len(unique_indices) > n_samples:
                unique_indices = np.random.choice(unique_indices, size=n_samples, replace=False)
            elif len(unique_indices) < n_samples:
                remaining = n_samples - len(unique_indices)
                available_indices = np.setdiff1d(np.arange(len(valid_data)), unique_indices)
                if len(available_indices) > 0:
                    additional_indices = np.random.choice(available_indices, 
                                                        size=min(remaining, len(available_indices)), 
                                                        replace=False)
                    unique_indices = np.concatenate([unique_indices, additional_indices])
                    
            return np.sort(unique_indices).astype(int)
            
        except Exception as e:
            logger.error(f"Error in representative sampling: {str(e)}")
            if len(valid_data) > 0:
                return np.random.choice(np.arange(len(valid_data)), 
                                      size=min(n_samples, len(valid_data)), 
                                      replace=False)
            return np.array([])

    def calculate_cpk(self, data: np.ndarray, lsl: float, usl: float, sensitivity: float = None) -> float:
        if sensitivity is None:
            sensitivity = self.sensitivity
        
        if pd.isna(lsl) and pd.isna(usl):
            return np.nan
            
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        
        if std == 0:
            return np.nan
            
        cpu = np.nan if pd.isna(usl) else (usl - mean) / (3 * std)
        cpl = np.nan if pd.isna(lsl) else (mean - lsl) / (3 * std)
        
        if pd.isna(cpu):
            cpk = cpl
        elif pd.isna(cpl):
            cpk = cpu
        else:
            cpk = min(cpu, cpl)
        
        sensitivity_factor = 1.0 - (sensitivity - 0.5) * 0.2
        adjusted_cpk = cpk * sensitivity_factor
        
        return round(adjusted_cpk, 2)

    def detect_outliers(self, data: np.ndarray, sensitivity: float = None) -> np.ndarray:
        if sensitivity is None:
            sensitivity = self.sensitivity
        
        z_threshold = 3.0 - (sensitivity * 1.5)
        
        z_scores = np.abs(stats.zscore(data))
        return z_scores > z_threshold

    def calculate_yield_metrics(self, data: np.ndarray, lsl: float, usl: float) -> Tuple[float, float, float]:
        total_count = len(data)
        if total_count == 0:
            return 0, 0, 0
            
        failures = 0
        if not pd.isna(lsl):
            failures += sum(data < lsl)
        if not pd.isna(usl):
            failures += sum(data > usl)
            
        yield_rate = round((total_count - failures) / total_count * 100, 2)
        yield_loss = round(failures / total_count * 100, 2)
        rejection_rate = round(failures / total_count * 100, 2)
        
        return yield_rate, yield_loss, rejection_rate 
    
    def calculate_percentiles(self, data: np.ndarray) -> Dict[str, float]:
        try:
            return {
                'p1': round(np.percentile(data, 1), 8),
                'p5': round(np.percentile(data, 5), 8),
                'p25': round(np.percentile(data, 25), 8),
                'p75': round(np.percentile(data, 75), 8),
                'p95': round(np.percentile(data, 95), 8),
                'p99': round(np.percentile(data, 99), 8)
            }
        except Exception:
            return {
                'p1': np.nan, 'p5': np.nan, 'p25': np.nan,
                'p75': np.nan, 'p95': np.nan, 'p99': np.nan
            }

    def process_single_file(self, input_file: str) -> Optional[pd.DataFrame]:
        try:
            df_input, _ = EFF.read(input_file)

            df_info_1 = EFF.get_value_rows(df_input, header='<+ParameterName>')
            lot_input = df_info_1['Lot'].iloc[0] if not df_info_1.empty else "Unknown"
            insertion_input = df_info_1['MeasStep'].iloc[0] if not df_info_1.empty else "Unknown"

            # Load reference data based on configuration
            reference_datasets = self._load_reference_data(insertion_input)
            
            if not reference_datasets:
                logger.warning(f"No reference data found for insertion: {insertion_input}")
                return None

            all_results = []
            
            # Process against each reference dataset
            for ref_idx, (df_reference, ref_metadata) in enumerate(reference_datasets):
                try:
                    df_info_2 = EFF.get_value_rows(df_reference, header='<+ParameterName>')
                    lot_reference = ref_metadata['lot']
                    insertion_reference = ref_metadata['insertion']
                    product_reference = ref_metadata['product']

                    # Analyze distribution similarity
                    df_new = analyze_distribution_similarity(
                        df_input, 
                        df_reference, 
                        self.selected_names, 
                        sensitivity=self.sensitivity,
                        model_version=self.model_version
                    )
                    
                    desc_rows = EFF.get_description_rows(df_input, header="<+ParameterName>")
                    
                    if self.selected_names is None:
                        available_tests = desc_rows.columns.tolist()
                    else:
                        available_tests = self.selected_names

                    current_selected_items = []
                    current_selected_numbers = []
                    
                    for test in available_tests:
                        if test in df_info_1.columns and test in df_info_2.columns:
                            current_selected_items.append(test)
                            test_number = desc_rows[test].loc['<+ParameterNumber>']
                            current_selected_numbers.append(str(test_number))

                    if not current_selected_items:
                        logger.warning(f"No common tests found between input and reference {ref_idx + 1}")
                        continue

                    columns = desc_rows[current_selected_items].loc['<+ParameterNumber>'].astype(str)
                    df_lsl1 = EFF.get_description_rows(df_input, header="<+ParameterName>").loc['<LIMIT:VALID:LOWER_VALUE>']
                    df_usl1 = EFF.get_description_rows(df_input, header="<+ParameterName>").loc['<LIMIT:VALID:UPPER_VALUE>']
                    df_lsl2 = EFF.get_description_rows(df_reference, header="<+ParameterName>").loc['<LIMIT:VALID:LOWER_VALUE>']
                    df_usl2 = EFF.get_description_rows(df_reference, header="<+ParameterName>").loc['<LIMIT:VALID:UPPER_VALUE>']
                    
                    def to_float_or_nan(arr):
                        return np.array([float(x) if str(x).strip() != '' else np.nan for x in arr])

                    lsl_input = to_float_or_nan(df_lsl1[current_selected_items].values)
                    usl_input = to_float_or_nan(df_usl1[current_selected_items].values)
                    lsl_reference = to_float_or_nan(df_lsl2[current_selected_items].values)
                    usl_reference = to_float_or_nan(df_usl2[current_selected_items].values)

                    TNUMBERS = list(columns)
                    
                    df_1 = EFF.get_value_rows(df_input, header='<+ParameterNumber>')[columns]
                    df_2 = EFF.get_value_rows(df_reference, header='<+ParameterNumber>')[columns]
                    
                    sample_indices_1 = self._get_representative_sample(df_1)
                    sample_indices_2 = self._get_representative_sample(df_2)
                    
                    sampled_data_1 = df_1.iloc[sample_indices_1]
                    sampled_data_2 = df_2.iloc[sample_indices_2]
                    
                    percentiles_input = []
                    percentiles_reference = []
                    for i, column in enumerate(columns):
                        percentiles_input.append(self.calculate_percentiles(sampled_data_1[column]))
                        percentiles_reference.append(self.calculate_percentiles(sampled_data_2[column]))
                    
                    result_df = pd.DataFrame()
                    result_df["Test Name"] = current_selected_items
                    result_df["Test Number"] = [int(float(t.strip())) for t in TNUMBERS]
                    result_df["lot_reference"] = lot_reference
                    result_df["lot_input"] = lot_input
                    result_df["insertion_reference"] = insertion_reference
                    result_df["insertion_input"] = insertion_input
                    result_df["reference_id"] = [f"REF_{product_reference}_{lot_reference}_{insertion_reference}_{t.strip()}" for t in TNUMBERS]
                    result_df["input_id"] = [f"IN_{product_reference}_{lot_input}_{insertion_input}_{t.strip()}" for t in TNUMBERS]
                    result_df["Product"] = product_reference
                    result_df["input_file"] = input_file
                    result_df["reference_source"] = ref_metadata['source']
                    result_df["reference_index"] = ref_idx + 1
                    
                    # Add reference file path for local files
                    if ref_metadata['source'] == 'local':
                        result_df["reference_file"] = ref_metadata.get('file_path', 'Unknown')
                    
                    df_filtered = df_new.reindex(TNUMBERS)

                    result_df["Status"] = df_filtered["target"].values
                    result_df["ML_Confidence"] = df_filtered["confidence_score"].values.round(4)
                    result_df["Sensitivity_Level"] = df_filtered["sensitivity_level"].values
                    result_df["Model_Version"] = df_filtered.get("model_version", self.model_version).values
                    
                    df1_description = sampled_data_1.describe().round(8).T
                    result_df["Min"] = df1_description["min"].values.round(8)
                    result_df["Max"] = df1_description["max"].values.round(8)
                    result_df["Mean"] = df1_description["mean"].values.round(8)
                    result_df["Std"] = df1_description["std"].values.round(8)

                    for metric in ['p1', 'p5', 'p25', 'p75', 'p95', 'p99']:
                        result_df[f'{metric}_input'] = [p[metric] for p in percentiles_input]
                        result_df[f'{metric}_reference'] = [p[metric] for p in percentiles_reference]

                    result_df["LSL_input"] = lsl_input.round(8)
                    result_df["USL_input"] = usl_input.round(8)
                    result_df["LSL_reference"] = lsl_reference.round(8)
                    result_df["USL_reference"] = usl_reference.round(8)
                    result_df["Confidence"] = [0.95] * len(current_selected_items)

                    input_data_dict = {}
                    reference_data_dict = {}
                    
                    for i, (test_name, t_number) in enumerate(zip(current_selected_items, TNUMBERS)):
                        if t_number in sampled_data_1.columns:
                            input_data_dict[test_name] = sampled_data_1[t_number].dropna().values.tolist()
                        else:
                            input_data_dict[test_name] = []
                            
                        if t_number in sampled_data_2.columns:
                            reference_data_dict[test_name] = sampled_data_2[t_number].dropna().values.tolist()
                        else:
                            reference_data_dict[test_name] = []

                    cpk_values = []
                    yield_values = []
                    yield_loss_values = []
                    rejection_rate_values = []

                    for test_name, t_number in zip(current_selected_items, TNUMBERS):
                        try:
                            if t_number not in sampled_data_1.columns:
                                cpk_values.append(np.nan)
                                yield_values.append(0)
                                yield_loss_values.append(0)
                                rejection_rate_values.append(0)
                                continue

                            input_data = sampled_data_1[t_number].values
                            
                            lsl_idx = list(columns).index(t_number) if t_number in columns else None
                            usl_idx = list(columns).index(t_number) if t_number in columns else None
                            
                            lsl = lsl_reference[lsl_idx] if lsl_idx is not None else np.nan
                            usl = usl_reference[usl_idx] if usl_idx is not None else np.nan

                            cpk = self.calculate_cpk(input_data, lsl, usl)
                            cpk_values.append(cpk)

                            yield_rate, yield_loss, rejection_rate = self.calculate_yield_metrics(input_data, lsl, usl)
                            yield_values.append(yield_rate)
                            yield_loss_values.append(yield_loss)
                            rejection_rate_values.append(rejection_rate)
                            
                        except Exception as e:
                            logger.error(f"Error processing test {t_number}: {str(e)}")
                            cpk_values.append(np.nan)
                            yield_values.append(0)
                            yield_loss_values.append(0)
                            rejection_rate_values.append(0)

                    result_df["Cpk"] = cpk_values
                    result_df["Yield"] = yield_values
                    result_df["Yield_Loss"] = yield_loss_values
                    result_df["Rejection_Rate"] = rejection_rate_values
                    
                    result_df["input_data"] = result_df["Test Name"].map(input_data_dict)
                    result_df["reference_data"] = result_df["Test Name"].map(reference_data_dict)
                    result_df["measurements"] = result_df["input_data"]
                    
                    all_results.append(result_df)
                    
                    logger.info(f"Processed reference dataset {ref_idx + 1}/{len(reference_datasets)} from {ref_metadata['source']}")
                    
                except Exception as e:
                    logger.error(f"Error processing reference dataset {ref_idx + 1}: {str(e)}")
                    continue
            
            # Combine all results if multiple reference datasets were processed
            if all_results:
                if len(all_results) == 1:
                    return all_results[0]
                else:
                    combined_result = pd.concat(all_results, ignore_index=True)
                    logger.info(f"Combined results from {len(all_results)} reference datasets")
                    return combined_result
            else:
                logger.warning("No results generated from any reference dataset")
                return None

        except Exception as e:
            logger.error(f"Error processing file {input_file}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def run(self):
        try:
            total_files = len(self.files)
            successful_results = []

            logger.info(f"Starting processing of {total_files} files with ML model (sensitivity: {self.sensitivity}, model: {self.model_version})")
            logger.info(f"Reference config: {self.reference_config}")

            for index, input_file in enumerate(self.files, 1):
                try:
                    result_df = self.process_single_file(input_file)
                    if result_df is not None:
                        successful_results.append(result_df)
                        self.file_processed.emit(input_file, True)
                        logger.info(f"Successfully processed file {index}/{total_files}: {Path(input_file).name}")
                    else:
                        self.file_processed.emit(input_file, False)
                        logger.error(f"Failed to process file {index}/{total_files}: {Path(input_file).name}")
                except Exception as e:
                    logger.error(f"Failed to process file {input_file}: {str(e)}")
                    self.file_processed.emit(input_file, False)
                    continue
                
                progress = (index * 100) // total_files
                self.progress.emit(progress)

            if successful_results:
                try:
                    combined_df = pd.concat(successful_results, ignore_index=True)
                    output_path = Path('test_results_analysis_ml.xlsx')
                    combined_df.to_excel(output_path, index=False)
                    
                    logger.info(f"Processing complete. Total rows: {len(combined_df)}")
                    logger.info(f"Files processed successfully: {len(successful_results)}/{total_files}")
                    
                    overall_status_counts = combined_df["Status"].value_counts()
                    overall_confidence_stats = combined_df["ML_Confidence"].describe()
                    logger.info(f"Overall ML Results:")
                    logger.info(f"  Status distribution: {overall_status_counts.to_dict()}")
                    logger.info(f"  Average confidence: {overall_confidence_stats['mean']:.3f}")
                    
                    # Log reference source distribution
                    if 'reference_source' in combined_df.columns:
                        source_counts = combined_df['reference_source'].value_counts()
                        logger.info(f"Reference source distribution: {source_counts.to_dict()}")
                    
                    null_input = combined_df['input_data'].isna().sum()
                    null_reference = combined_df['reference_data'].isna().sum()
                    logger.info(f"Data integrity: Null input_data: {null_input}, Null reference_data: {null_reference}")
                    
                    self.result.emit(combined_df)
                except Exception as e:
                    logger.error(f"Error combining results: {str(e)}")
                    if successful_results:
                        self.result.emit(successful_results[0])
            else:
                self.error.emit("No files were processed successfully")

        except Exception as e:
            logger.error(f"Fatal error in processing: {str(e)}")
            self.error.emit(f"Fatal error occurred: {str(e)}")
        finally:
            self.finished.emit()