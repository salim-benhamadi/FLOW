import xml.etree.ElementTree as ET
from datetime import datetime
from ui.utils.Effio import EFF
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class EFFProcessor:
    def __init__(self, api_client, sample_size: int = 201):
        self.api_client = api_client
        self.sample_size = sample_size
    
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
            
            unique_indices = [int(i) for i in unique_indices if i.isdigit()]
            return np.sort(unique_indices).astype(int)
            
        except Exception as e:
            logger.error(f"Error in representative sampling: {str(e)}")
            if len(valid_data) > 0:
                return np.random.choice(np.arange(len(valid_data)), 
                                      size=min(n_samples, len(valid_data)), 
                                      replace=False)
            return np.array([])

    async def process_eff_file(self, file_path: str, product: str, lot: str, insertion: str) -> dict:
        try:
            logger.debug("Starting EFF file processing: %s", file_path)
            product = product.upper()
            lot = lot.upper()
            insertion = insertion.upper()
            
            df, _ = EFF.read(file_path)
            header_info = EFF.get_description_rows(df, header="<+ParameterName>")
            mask = df.loc['<+ParameterNumber>'].apply(lambda x: str(x).isdigit())
            test_names = df.loc['<+ParameterName>'][mask].tolist()
            test_numbers = df.loc['<+ParameterNumber>'][mask].tolist()
            
            lsls = EFF.lsl(df, test_numbers)
            usls = EFF.usl(df, test_numbers)
            
            measurements_df = EFF.get_value_rows(df, fix_dtypes=True, header="<+ParameterName>")[test_names].fillna(0)
            sample_indices = self._get_representative_sample(measurements_df, self.sample_size)
            measurements_df = measurements_df.iloc[sample_indices, :]
            
            reference_ids = []
            for test_idx, test_name in enumerate(test_names):
                reference_id = f"REF_{product}_{lot}_{insertion}_{test_numbers[test_idx]}"
                if reference_id in reference_ids:
                    continue
                    
                reference_ids.append(reference_id)
                reference_data = {
                    'reference_id': reference_id,
                    'product': product,
                    'lot': lot,
                    'insertion': insertion,
                    'test_name': test_name,
                    'test_number': test_numbers[test_idx],
                    'lsl': float(lsls[test_idx]) if not np.isnan(lsls[test_idx]) else None,
                    'usl': float(usls[test_idx]) if not np.isnan(usls[test_idx]) else None,
                    'measurements': [
                        {
                            'chip_number': int(i + 1),
                            'value': float(val) if not np.isnan(val) else None
                        }
                        for i, val in enumerate(measurements_df[test_name])
                    ]
                }
                await self.api_client.save_reference_data(reference_data)
                
            return {
                'status': 'success',
                'reference_ids': reference_ids,
                'message': 'EFF file processed successfully',
                'measurements_count': len(sample_indices),
                'tests_count': len(test_names)
            }

        except Exception as e:
            logger.error("Error processing EFF file: %s", str(e), exc_info=True)
            raise Exception(f"Error processing EFF file: {str(e)}")