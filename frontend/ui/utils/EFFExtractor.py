import os
import subprocess
import concurrent.futures
import pathlib
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional
from ui.utils.PathResources import resource_path

class ExtractorType(Enum):
    BACKEND = "BE"
    FRONTEND = "FE"

@dataclass
class ExtractionConfig:
    xml_name: str
    required_params: List[str]

class EFFExtractor:
    CONFIG_MAP = {
        ExtractorType.BACKEND: ExtractionConfig(
            xml_name="BE.xml",
            required_params=["Lot", "MeasStep"]
        ),
        ExtractorType.FRONTEND: ExtractionConfig(
            xml_name="FE.xml",
            required_params=["Lot", "Wafer", "MeasStep"]
        )
    }

    def __init__(self, extractor_type: ExtractorType):
        self.extractor_type = extractor_type
        self.config = self.CONFIG_MAP[extractor_type]
        self.root_dir = pathlib.Path().absolute()

    def write_bat_file(self, bat_path: str, xml_path: str, params: dict, testList: str, delivery_path: str) -> None:
        """Creates a batch file for eSquare extraction with flexible parameters"""
        with open(bat_path, 'w') as bat_file:
            bat_file.write('c:\n')
            if os.path.exists('C:\\Program Files\\eSquare_x64_2.8.6.3\\'):
                bat_file.write('cd C:\Program Files\eSquare_x64_2.8.6.3\ \n')
            else:
                raise RuntimeError('Error: You need to install eSquare version 2.8.6.3 to proceed!')
            bat_file.write('\n')
            
            # Build parameter string
            param_str = ' '.join([f'-p [(]{k}[)]="{v}"' for k, v in params.items()])
            bat_file.write(rf'e2runjob -f "{xml_path}" {param_str} -p [(]TestList[)]="{testList}" -o -d "{delivery_path}"')

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

    def validate_params(self, lot: str, wafer: Optional[str], insertions: List[str]) -> None:
        """Validates parameters based on extractor type"""
        if not lot:
            raise ValueError("Lot number is required")
        
        if self.extractor_type == ExtractorType.FRONTEND and not wafer:
            raise ValueError("Wafer is required for frontend extraction")

    def extract_eff(self, lot: str, insertions: List[str], wafer: Optional[str] = None) -> List[str]:
        """Main function to extract EFF files with support for both BE and FE"""
        self.validate_params(lot, wafer, insertions)
        
        xml_path = resource_path(os.path.join('./resources/config', self.config.xml_name))
        eff_files_path = resource_path('\resources\output')
        batch_files = []

        # Create necessary directories
        log_path = resource_path(os.path.join('./resources/config', f'{self.extractor_type.value}-extraction-logs'))
        os.makedirs(log_path, exist_ok=True)
        os.makedirs(eff_files_path, exist_ok=True)

        # Handle all insertions case
        if insertions[0] == '*' and self.extractor_type == ExtractorType.BACKEND:
            insertions = ['B1','B2','B3','B4','B5','B6','B7']
        
        if insertions[0] == '*' and self.extractor_type == ExtractorType.FRONTEND:
            insertions = ['S1', 'S2']

        for meas_step in insertions:
            # Prepare parameters based on extractor type
            params = {"Lot": lot, "MeasStep": meas_step}
            if self.extractor_type == ExtractorType.FRONTEND and wafer:
                params["Wafer"] = wafer

            file_suffix = f"{lot}-{meas_step}"
            if wafer:
                file_suffix = f"{file_suffix}-{wafer}"
                
            bat_path = resource_path(os.path.join(log_path, f'{file_suffix}.bat'))
            batch_files.append(bat_path)
            self.write_bat_file(bat_path, xml_path, params, '*', eff_files_path)

        # Execute all batch files concurrently
        with concurrent.futures.ThreadPoolExecutor() as executor:
            extraction_status = list(executor.map(self.start_batch, batch_files))
            
        return extraction_status
