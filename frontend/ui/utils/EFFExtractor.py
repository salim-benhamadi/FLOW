import os
import subprocess
import concurrent.futures
import pathlib
from typing import List, Tuple, Dict
from enum import Enum

class ExtractorType(Enum):
    BACKEND = "BE"
    FRONTEND = "FE"

class EFFExtractor:
    @staticmethod
    def write_bat_file(bat_path: str, xml_path: str, lot: str, meas_step: str, testList: str, delivery_path: str) -> None:
        """Creates a batch file for eSquare extraction"""
        with open(bat_path, 'w') as bat_file:           
            bat_file.write('c:\n')
            if os.path.exists('C:\\Program Files\\eSquare_x64_2.8.6.3\\'):            
                bat_file.write('cd C:\Program Files\eSquare_x64_2.8.6.3\ \n')
            else:
                raise RuntimeError('Error: You need to install eSquare version 2.8.6.3 to proceed!')
            bat_file.write('\n')
            bat_file.write(rf'e2runjob -f "{xml_path}" -p [(]Lot[)]="{lot}" -p [(]MeasStep[)]="{meas_step}" -p [(]TestList[)]="{testList}" -o -d "{delivery_path}"')

    @staticmethod
    def start_batch(bat_file_path: str) -> str:
        """Executes batch file and returns the last line of output"""
        process = subprocess.Popen(bat_file_path, shell=True, stdout=subprocess.PIPE, text=True)
        log_path = bat_file_path.replace("bat", "txt") 
        output, _ = process.communicate()
        output_lines = output.splitlines()
        last_line = output_lines[-1] if output_lines else "No output"
        with open(log_path, 'w') as log_file:
            log_file.write(output)  
        return last_line

    @staticmethod
    def create_output_directories(root_dir: pathlib.Path) -> Dict[str, str]:
        """Creates necessary directories for output and logs"""
        paths = {
            'log': os.path.join(root_dir, 'config', 'lot-extraction-logs'),
            'eff_be': os.path.join(root_dir, 'output', 'backend'),
            'eff_fe': os.path.join(root_dir, 'output', 'frontend')
        }
        
        for path in paths.values():
            os.makedirs(path, exist_ok=True)
            
        return paths

    @staticmethod
    def extract_lot_eff(lot: str, insertions: List[str], extractor_type: ExtractorType = ExtractorType.BACKEND) -> List[str]:
        """
        Main function to extract lot level EFF files for both backend and frontend
        
        Args:
            lot: Lot number
            insertions: List of insertion steps to process
            extractor_type: Type of extraction (BE or FE)
            
        Returns:
            List of extraction status messages
        """
        root_dir = pathlib.Path().absolute()
        xml_path = os.path.join(root_dir, 'config', f'{extractor_type.value}.xml')
        paths = EFFExtractor.create_output_directories(root_dir)
        
        # Select appropriate output directory based on extractor type
        eff_files_path = paths['eff_be'] if extractor_type == ExtractorType.BACKEND else paths['eff_fe']
        batch_files = []

        for meas_step in insertions:
            bat_path = os.path.join(paths['log'], f'{lot}-{meas_step}-{extractor_type.value}.bat')
            batch_files.append(bat_path)
            EFFExtractor.write_bat_file(bat_path, xml_path, lot, meas_step, '*', eff_files_path)

        # Execute all batch files concurrently
        with concurrent.futures.ThreadPoolExecutor() as executor:
            extraction_status = list(executor.map(EFFExtractor.start_batch, batch_files))
            
        return extraction_status

    @staticmethod
    def extract_lot_eff_both(lot: str, insertions: List[str]) -> Dict[str, List[str]]:
        """
        Extract both backend and frontend EFF files
        
        Args:
            lot: Lot number
            insertions: List of insertion steps to process
            
        Returns:
            Dictionary containing extraction status for both BE and FE
        """
        results = {
            'backend': EFFExtractor.extract_lot_eff(lot, insertions, ExtractorType.BACKEND),
            'frontend': EFFExtractor.extract_lot_eff(lot, insertions, ExtractorType.FRONTEND)
        }
        return results