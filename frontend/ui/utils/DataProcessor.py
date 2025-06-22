from PySide6.QtCore import Signal, QThread
from ui.utils.Model import analyze_distribution_similarity
from ui.utils.Effio import EFF
import pandas as pd
import numpy as np
import random
import re
import logging
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path
from ui.utils.PathResources import resource_path
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataProcessor(QThread):
    progress = Signal(int)
    finished = Signal()
    result = Signal(object)
    error = Signal(str)
    file_processed = Signal(str, bool)

    VAMOS_TEST = {
        "VAMOS_PU": [6000, 6999],
        "VAMOS_CFS": [7000, 7999],
        "VAMOS_IDD": [10000, 19999],
        "VAMOS_PMU": [20000, 29999],
        "VAMOS_GPIO": [30000, 39999],
        "VAMOS_OSC": [40000, 49999],
        "VAMOS_ATPG": [50000, 59999],
        "VAMOS_IDDQ": [60000, 69999],
        "VAMOS_MEM": [70000, 79999],
        "VAMOS_UM": [80000, 89999],
        "VAMOS_LIB": [90000, 99999],
        "VAMOS_spare": [100000, 109999]
    }

    def __init__(self, selected_items: Optional[List[str]] = None, files: List[str] = None, 
                 sensitivity: float = 0.5):
        super().__init__()
        if not files:
            raise ValueError("Files cannot be empty")
        
        self.files = [str(Path(f).resolve()) for f in files]
        
        # Handle selected_items - if None or empty, use all available tests
        if selected_items:
            self.selected_items = [item.split(";")[1] for item in selected_items]
            self.selected_numbers = [item.split(";")[0] for item in selected_items]
            self.selected_names = [item.split(";")[1] for item in selected_items]
        else:
            self.selected_items = None
            self.selected_numbers = None
            self.selected_names = None
            
        self.sensitivity = sensitivity
        self.results = []
        self._processed_count = 0

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

    def calculate_cpk(self, data: np.ndarray, lsl: float, usl: float) -> float:
        if pd.isna(lsl) and pd.isna(usl):
            return np.nan
            
        mean = np.mean(data)
        std = np.std(data, ddof=1)
        
        if std == 0:
            return np.nan
            
        cpu = np.nan if pd.isna(usl) else (usl - mean) / (3 * std)
        cpl = np.nan if pd.isna(lsl) else (mean - lsl) / (3 * std)
        
        if pd.isna(cpu):
            return round(cpl, 2)
        elif pd.isna(cpl):
            return round(cpu, 2)
        else:
            return round(min(cpu, cpl), 2)

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

    def get_module(self, test_number: Union[int, str]) -> str:
        try:
            test_num = int(float(test_number))
            for module, (start, end) in self.VAMOS_TEST.items():
                if start <= test_num <= end:
                    return module
            return "Unknown"
        except (ValueError, TypeError):
            return "Unknown"

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
            # Input data extraction
            df_input, _ = EFF.read(input_file)

            df_info_1 = EFF.get_value_rows(df_input, header='<+ParameterName>')
            lot_input = df_info_1['Lot'].iloc[0] if not df_info_1.empty else "Unknown"
            insertion_input = df_info_1['MeasStep'].iloc[0] if not df_info_1.empty else "Unknown"

            # Reference data extraction
            reference_path = resource_path(f'resources/output/ZA407235G04_{insertion_input}.eff')
            if not Path(reference_path).exists():
                reference_path = resource_path(f'resources/output/ZA407235G04_B1.eff')
            df_ref, _ = EFF.read(reference_path)
            df_info_2 = EFF.get_value_rows(df_ref, header='<+ParameterName>')
            lot_reference = df_info_2['Lot'].iloc[0] if not df_info_2.empty else "Unknown"
            insertion_reference = df_info_2['MeasStep'].iloc[0] if not df_info_2.empty else "Unknown"

            # Determine which tests to analyze
            current_selected_items = self.selected_items
            if current_selected_items is None:
                # Use all available tests
                desc_rows = EFF.get_description_rows(df_input, header="<+ParameterName>")
                mask = desc_rows.loc['<+ParameterNumber>'].apply(lambda x: str(x).isdigit())
                current_selected_items = desc_rows.columns[mask].tolist()
                logger.info(f"Using all {len(current_selected_items)} available tests")

            TNUMBERS = EFF.get_description_rows(df_input, header="<+ParameterName>")[current_selected_items].loc['<+ParameterNumber>']
            TNUMBERS = TNUMBERS.astype(str)
            
            df_testdata_1_full = EFF.get_value_rows(df_input, header='<+ParameterNumber>', fix_dtypes=True)
            df_testdata_2_full = EFF.get_value_rows(df_ref, header='<+ParameterNumber>', fix_dtypes=True)
            
            df_testdata_1_full.columns = df_testdata_1_full.columns.astype(str)
            df_testdata_2_full.columns = df_testdata_2_full.columns.astype(str)

            # Create dictionaries keyed by test name instead of test number
            input_data_dict = {}
            reference_data_dict = {}
            sampled_data_1 = pd.DataFrame()
            sampled_data_2 = pd.DataFrame()

            for idx, t_number in enumerate(TNUMBERS):
                test_name = current_selected_items[idx]
                
                if t_number not in df_testdata_1_full.columns or t_number not in df_testdata_2_full.columns:
                    input_data_dict[test_name] = []
                    reference_data_dict[test_name] = []
                    logger.warning(f"Test number {t_number} not found in data columns for test {test_name}")
                    continue

                input_series = df_testdata_1_full[t_number].dropna()
                reference_series = df_testdata_2_full[t_number].dropna()
                
                if len(input_series) == 0 or len(reference_series) == 0:
                    input_data_dict[test_name] = []
                    reference_data_dict[test_name] = []
                    logger.warning(f"No valid data for test {test_name} (number: {t_number})")
                    continue
                    
                input_df = pd.DataFrame({t_number: input_series})
                reference_df = pd.DataFrame({t_number: reference_series})
                
                input_indices = self._get_representative_sample(input_df)
                reference_indices = self._get_representative_sample(reference_df)
                
                if len(input_indices) > 0 and len(reference_indices) > 0:
                    sampled_input = input_series.iloc[input_indices]
                    sampled_reference = reference_series.iloc[reference_indices]
                    sampled_data_1[t_number] = sampled_input.reset_index(drop=True)
                    sampled_data_2[t_number] = sampled_reference.reset_index(drop=True)
                    
                    # Store data with test name as key
                    input_data_dict[test_name] = sampled_input.tolist()
                    reference_data_dict[test_name] = sampled_reference.tolist()
                    
                    logger.info(f"Stored data for test {test_name}: input={len(sampled_input)}, reference={len(sampled_reference)}")
                else:
                    input_data_dict[test_name] = []
                    reference_data_dict[test_name] = []
                    logger.warning(f"No sampled indices for test {test_name}")

            columns = list(sampled_data_1.columns)
            total_columns = len(columns)

            if total_columns == 0:
                logger.error("No valid test data found in file")
                return None

            # Use ML model for distribution analysis instead of statistical method
            logger.info(f"Analyzing {total_columns} tests using ML model with sensitivity {self.sensitivity}")
            
            try:
                # Call the ML-based analyze_distribution_similarity function
                df_new = analyze_distribution_similarity(df_input, df_ref, current_selected_items, self.sensitivity)
                logger.info("ML analysis completed successfully")
            except Exception as e:
                logger.error(f"ML analysis failed: {str(e)}")
                raise
            
            # Get LSL/USL values
            lsl_input = EFF.lsl(df_input, columns)
            usl_input = EFF.usl(df_input, columns)
            lsl_reference = EFF.lsl(df_ref, columns)
            usl_reference = EFF.usl(df_ref, columns)

            # Calculate percentiles for compatibility
            percentiles_input = []
            percentiles_reference = []
            for i, column in enumerate(columns):
                percentiles_input.append(self.calculate_percentiles(sampled_data_1[column]))
                percentiles_reference.append(self.calculate_percentiles(sampled_data_2[column]))
            
            # Create result DataFrame
            result_df = pd.DataFrame()
            result_df["Test Name"] = current_selected_items
            result_df["Test Number"] = [int(float(t.strip())) for t in TNUMBERS]
            result_df["lot_reference"] = lot_reference
            result_df["lot_input"] = lot_input
            result_df["insertion_reference"] = insertion_reference
            result_df["insertion_input"] = insertion_input
            result_df["reference_id"] = [f"REF_AJAX_{lot_reference}_{insertion_reference}_{t.strip()}" for t in TNUMBERS]
            result_df["input_id"] = [f"IN_AJAX_{lot_input}_{insertion_input}_{t.strip()}" for t in TNUMBERS]
            result_df["Product"] = "AJAX"
            result_df["input_file"] = input_file
            
            # Filter ML results to match our test numbers
            df_filtered = df_new.reindex(TNUMBERS)

            # Get ML predictions and confidence scores
            result_df["Status"] = df_filtered["target"].values
            result_df["ML_Confidence"] = df_filtered["confidence_score"].values.round(4)
            result_df["Sensitivity_Level"] = df_filtered["sensitivity_level"].values
            
            # Calculate basic statistics from sampled data
            df1_description = sampled_data_1.describe().round(8).T
            result_df["Min"] = df1_description["min"].values.round(8)
            result_df["Max"] = df1_description["max"].values.round(8)
            result_df["Mean"] = df1_description["mean"].values.round(8)
            result_df["Std"] = df1_description["std"].values.round(8)

            # Add percentiles
            for metric in ['p1', 'p5', 'p25', 'p75', 'p95', 'p99']:
                result_df[f'{metric}_input'] = [p[metric] for p in percentiles_input]
                result_df[f'{metric}_reference'] = [p[metric] for p in percentiles_reference]

            # Add specification limits
            result_df["LSL_input"] = lsl_input.round(8)
            result_df["USL_input"] = usl_input.round(8)
            result_df["LSL_reference"] = lsl_reference.round(8)
            result_df["USL_reference"] = usl_reference.round(8)
            result_df["Confidence"] = [0.95] * len(current_selected_items)

            # Calculate Cpk and yield metrics
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
                    
                    # Use reference limits for Cpk calculation
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
            result_df["Module"] = result_df["Test Number"].map(self.get_module)
            
            # Map using Test Name (which is the key in our dictionaries)
            result_df["input_data"] = result_df["Test Name"].map(input_data_dict)
            result_df["reference_data"] = result_df["Test Name"].map(reference_data_dict)
            
            # Add measurements column for compatibility
            result_df["measurements"] = result_df["input_data"]
            
            # Debug logging
            logger.info(f"Data mapping results:")
            for idx, row in result_df.iterrows():
                test_name = row["Test Name"]
                has_input = test_name in input_data_dict and len(input_data_dict[test_name]) > 0
                has_reference = test_name in reference_data_dict and len(reference_data_dict[test_name]) > 0
                logger.info(f"  {test_name}: input_data={has_input}, reference_data={has_reference}")

            # Log ML prediction summary
            status_counts = result_df["Status"].value_counts()
            confidence_stats = result_df["ML_Confidence"].describe()
            logger.info(f"ML Prediction Summary:")
            logger.info(f"  Status distribution: {status_counts.to_dict()}")
            logger.info(f"  Confidence stats: mean={confidence_stats['mean']:.3f}, min={confidence_stats['min']:.3f}, max={confidence_stats['max']:.3f}")

            return result_df

        except Exception as e:
            logger.error(f"Error processing file {input_file}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def run(self):
        try:
            total_files = len(self.files)
            successful_results = []

            logger.info(f"Starting processing of {total_files} files with ML model (sensitivity: {self.sensitivity})")

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
                    
                    # Log summary of results
                    logger.info(f"Processing complete. Total rows: {len(combined_df)}")
                    logger.info(f"Files processed successfully: {len(successful_results)}/{total_files}")
                    
                    # ML-specific summary
                    overall_status_counts = combined_df["Status"].value_counts()
                    overall_confidence_stats = combined_df["ML_Confidence"].describe()
                    logger.info(f"Overall ML Results:")
                    logger.info(f"  Status distribution: {overall_status_counts.to_dict()}")
                    logger.info(f"  Average confidence: {overall_confidence_stats['mean']:.3f}")
                    
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