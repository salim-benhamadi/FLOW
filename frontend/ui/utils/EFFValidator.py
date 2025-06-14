from typing import Dict, List, Tuple
import re
from PySide6.QtWidgets import QMessageBox
import os

class EFFValidator:
    def __init__(self):
        self.param_name_pattern = re.compile(r'<\+ParameterName>;(.+)$')
        self.param_number_pattern = re.compile(r'<\+ParameterNumber>;(.+)$')

    def validate_eff_files(self, unified_data: Dict) -> Tuple[bool, str]:
        """
        Validates all EFF files to ensure proper tag structure and IsPass presence.
        Stops checking when a non-tag line is encountered.
        
        Args:
            unified_data: Dictionary containing file paths and other metadata
            
        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        try:
            for insertion, data in unified_data.items():
                for file_path in data['FILES']:
                    if not os.path.exists(file_path):
                        return False, f"File not found: {file_path}"
                    
                    with open(file_path, 'r', encoding='utf-8') as file:
                        # Track if required tags are found
                        param_name_found = False
                        param_number_found = False
                        ispass_found = False
                        
                        for line in file:
                            # Break if line doesn't start with '<'
                            if not line.strip().startswith('<'):
                                break
                            
                            # Check for ParameterName
                            name_match = self.param_name_pattern.search(line)
                            if name_match:
                                param_name_found = True
                                # Check if IsPass exists in ParameterName row
                                param_name_content = name_match.group(1)
                                if 'IsPass' in param_name_content:
                                    ispass_found = True
                                continue
                            
                            # Check for ParameterNumber
                            number_match = self.param_number_pattern.search(line)
                            if number_match:
                                param_number_found = True
                                continue
                        
                        # Validate all requirements were met
                        if not param_name_found:
                            return False, f"Missing <+ParameterName> tag in file: {os.path.basename(file_path)}"
                            
                        if not param_number_found:
                            return False, f"Missing <+ParameterNumber> tag in file: {os.path.basename(file_path)}"
                            
                        if not ispass_found:
                            return False, f"'IsPass' not found in <+ParameterName> row in file: {os.path.basename(file_path)}"
            
            return True, "All files validated successfully"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"