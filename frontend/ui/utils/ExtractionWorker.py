from PySide6.QtCore import QThread, Signal
from typing import List, Dict, Optional
import os
import concurrent.futures
from ui.utils.EFFExtractor import EFFExtractor
import sys
import os

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class ExtractionWorker(QThread):
    progress = Signal(str, int, str, float)
    finished = Signal(list)
    file_created = Signal(str)
    
    def __init__(self, lot: str, insertions: List[str], extractor: EFFExtractor, wafer: Optional[str] = None, max_workers: int = None):
        super().__init__()
        self.lot = lot
        self.insertions = insertions
        self.extractor = extractor
        self.wafer = wafer
        self.max_workers = max_workers or min(len(insertions), os.cpu_count() or 4)
        self._status_dict = {}

    def _process_insertion(self, insertion: str) -> Dict:
        try:
            if self.wafer:
                filename = f"{self.lot}_{self.wafer}_{insertion}.eff"
            else:
                filename = f"{self.lot}_{insertion}.eff"
            
            created_file_path = resource_path(f"./resources/output/{filename}")
            
            if self.wafer:
                status = self.extractor.extract_eff(self.lot, [insertion], self.wafer)
            else:
                status = self.extractor.extract_eff(self.lot, [insertion])
            
            if os.path.exists(created_file_path):
                real_filename = os.path.basename(created_file_path)
                filesize = os.path.getsize(created_file_path) / 1024.0
            else:
                real_filename = filename
                filesize = 0.0
                
            return {
                'insertion': insertion,
                'status': status,
                'filename': filename,
                'real_filename': real_filename,
                'filesize': filesize,
                'file_path': created_file_path
            }
        except Exception as e:
            return {
                'insertion': insertion,
                'status': [str(e)],
                'filename': filename,
                'error': str(e)
            }

    def _update_progress(self):
        completed = len(self._status_dict)
        total = len(self.insertions)
        progress = int((completed / total) * 100)
        
        for result in self._status_dict.values():
            self.progress.emit(
                result['filename'],
                progress,
                result.get('real_filename', result['filename']),
                result.get('filesize', 0.0)
            )

    def run(self):
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_insertion = {
                    executor.submit(self._process_insertion, insertion): insertion 
                    for insertion in self.insertions
                }
                
                for future in concurrent.futures.as_completed(future_to_insertion):
                    insertion = future_to_insertion[future]
                    try:
                        result = future.result()
                        self._status_dict[insertion] = result
                        
                        if 'file_path' in result:
                            self.file_created.emit(result['file_path'])
                        
                        self._update_progress()
                        
                    except Exception as e:
                        self._status_dict[insertion] = {
                            'insertion': insertion,
                            'status': [f"Error processing {insertion}: {str(e)}"],
                            'error': str(e)
                        }
            
            status_list = [
                result['status'] 
                for result in self._status_dict.values()
            ]
            self.finished.emit(status_list)
            
        except Exception as e:
            self.finished.emit([str(e)])