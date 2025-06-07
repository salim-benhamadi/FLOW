import numpy as np
from scipy import stats
import pandas as pd

def analyze_distribution_similarity(df):
    """
    Analyze distribution similarity between input and reference data
    Returns dataframe with original data and similarity analysis results
    
    Parameters:
    df (pandas.DataFrame): DataFrame with columns for input and reference measurements
    
    Returns:
    pandas.DataFrame: Original data with additional analysis columns
    """
    results = []
    
    # XYZ rating thresholds
    x_criteria = {
        'A': {'mean_diff': 20, 'std_diff': 30, 'quartile_diff': 30},
        'B': {'mean_diff': 50, 'std_diff': 70, 'quartile_diff': 70},
        'C': {'mean_diff': 100, 'std_diff': 100, 'quartile_diff': 100},
        'D': {'mean_diff': 200, 'std_diff': 150, 'quartile_diff': 150}
    }
    
    # Sync class thresholds (from Tech Sync method)
    sync_class_1 = {'rdrs': 0.8, 'pratio': 1.2}
    sync_class_2 = {'rdrs': 1.5, 'pratio': 2.0}
    
    for idx in df.index:
        row = df.loc[idx]
        
        # Calculate Relative Deviation (RDRS)
        if row['mean_reference'] == 0 and row['mean_input'] == 0:
            rd_rs = 0
        else:
            median_diff = abs(row['mean_input'] - row['mean_reference'])
            iqr_rs = row['p75_reference'] - row['p25_reference']
            rd_rs = median_diff / (iqr_rs + 1e-10)
        
        # Calculate Percentile Ratio (PRatio)
        iqr_ts = row['p75_input'] - row['p25_input']
        iqr_rs = row['p75_reference'] - row['p25_reference']
        if iqr_rs == 0 and iqr_ts == 0:
            p_ratio = 1
        else:
            p_ratio = iqr_ts / (iqr_rs + 1e-10)
        
        # Calculate relative differences for mean and std
        if row['mean_reference'] == 0 and row['mean_input'] == 0:
            mean_rel_diff = 0
        else:
            mean_rel_diff = abs(row['mean_input'] - row['mean_reference']) / (abs(row['mean_reference']) + 1e-10) * 100
            
        if row['std_reference'] == 0 and row['std_input'] == 0:
            std_rel_diff = 0
        else:
            std_rel_diff = abs(row['std_input'] - row['std_reference']) / (row['std_reference'] + 1e-10) * 100

        # Calculate quartile differences
        q1_diff = abs(row['p25_input'] - row['p25_reference'])
        q3_diff = abs(row['p75_input'] - row['p75_reference'])
        
        iqr_reference = row['p75_reference'] - row['p25_reference']
        if iqr_reference == 0 and (row['p75_input'] - row['p25_input']) == 0:
            q1_rel_diff = 0
            q3_rel_diff = 0
        else:
            q1_rel_diff = q1_diff / (iqr_reference + 1e-10) * 100
            q3_rel_diff = q3_diff / (iqr_reference + 1e-10) * 100
        
        quartile_diff = max(q1_rel_diff, q3_rel_diff)
        
        # Check specification limits
        limits_match = True
        if not pd.isna(row.get('lsl_input', None)) and not pd.isna(row.get('lsl_reference', None)):
            if row['lsl_reference'] == 0 and row['lsl_input'] == 0:
                lsl_rel_diff = 0
            else:
                lsl_rel_diff = abs(row['lsl_input'] - row['lsl_reference']) / (abs(row['lsl_reference']) + 1e-10) * 100
            limits_match = limits_match and (lsl_rel_diff < 15)
            
        if not pd.isna(row.get('usl_input', None)) and not pd.isna(row.get('usl_reference', None)):
            if row['usl_reference'] == 0 and row['usl_input'] == 0:
                usl_rel_diff = 0
            else:
                usl_rel_diff = abs(row['usl_input'] - row['usl_reference']) / (abs(row['usl_reference']) + 1e-10) * 100
            limits_match = limits_match and (usl_rel_diff < 15)

        # Calculate additional statistical measures
        skew_diff = abs(row.get('skew_input', 0) - row.get('skew_reference', 0))
        kurt_diff = abs(row.get('kurt_input', 0) - row.get('kurt_reference', 0))
        
        # Determine synchronization class and category based on Tech Sync method
        if ((rd_rs <= sync_class_1['rdrs'] and p_ratio <= sync_class_1['pratio']) or
            (rd_rs <= sync_class_2['rdrs'] and p_ratio <= sync_class_2['pratio'])):
            # Class 1 or 2
            target = 'Similar distribution'
            
        elif (mean_rel_diff <= x_criteria['C']['mean_diff'] and
              std_rel_diff <= x_criteria['C']['std_diff'] and
              quartile_diff <= x_criteria['C']['quartile_diff']):
            # Class 3
            target = 'Moderately similar'
            
        else:
            # Class 4
            target = 'Completely different'
        
        # Special case for zero mean and std
        if (row['mean_reference'] == row['mean_input'] and 
            row['std_reference'] == 0 and row['std_input'] == 0):
            if skew_diff <= 0.2 and kurt_diff <= 0.4:
                target = 'Similar distribution'
            elif skew_diff <= 0.6 and kurt_diff <= 1.0:
                target = 'Moderately similar'
        
        results.append({
            'index': idx,
            'target': target,
            'mean_diff_pct': mean_rel_diff,
            'std_diff_pct': std_rel_diff,
            'q1_diff_pct': q1_rel_diff,
            'q3_diff_pct': q3_rel_diff,
            'skew_diff': skew_diff,
            'kurt_diff': kurt_diff,
            'limits_match': limits_match,
            'rdrs': rd_rs,
            'pratio': p_ratio
        })
    
    result_df = pd.DataFrame(results).set_index('index')
    
    final_df = pd.concat([df, result_df[['target', 'mean_diff_pct', 'std_diff_pct', 
                                        'q1_diff_pct', 'q3_diff_pct', 'skew_diff',
                                        'kurt_diff', 'limits_match', 'rdrs', 'pratio']]], axis=1)
    
    return final_df