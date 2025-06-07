from PySide6.QtCore import QThread, Signal
from typing import List
import os
from ui.utils.EFFExtractor import EFFExtractor

class ExtractionType:
    BACKEND = "BE"
    FRONTEND = "FE"

class ExtractionWorker(QThread):
    progress = Signal(str, int, str, float)
    finished = Signal(list)
    file_created = Signal(str)
    
    def __init__(self, lot: str, insertions: List[str], extractor: EFFExtractor, extraction_type: str):
        super().__init__()
        self.lot = lot
        self.insertions = insertions
        self.extractor = extractor
        self.extraction_type = extraction_type
        self._is_running = True

    def stop(self):
        """Safely stop the worker thread"""
        self._is_running = False
        self.wait()

    def run(self):
        try:
            status_list = []
            total_insertions = len(self.insertions)
            
            for idx, insertion in enumerate(self.insertions, 1):
                if not self._is_running:
                    self.finished.emit([("Stopped", "Extraction stopped by user")])
                    return

                # Calculate progress percentage
                progress = int((idx - 1) / total_insertions * 100)
                
                # Create filename based on extraction type
                type_prefix = "BE" if self.extraction_type == ExtractionType.BACKEND else "FE"
                filename = f"{self.lot}_{type_prefix}_{insertion}.eff"
                
                # Extract the file using the extract_lot_eff method
                status = self.extractor.extract_lot_eff(self.lot, [insertion])
                created_file_path = f"./output/{filename}"
                
                if os.path.exists(created_file_path):
                    real_filename = os.path.basename(created_file_path)
                    filesize = os.path.getsize(created_file_path) / 1024.0  # KB
                else:
                    real_filename = filename
                    filesize = 0.0
                
                self.progress.emit(filename, progress, real_filename, filesize)
                status_list.append(status)
                self.file_created.emit(created_file_path)
                
                # Update progress to 100% for this file
                self.progress.emit(filename, 100, real_filename, filesize)
            
            self.finished.emit(status_list)
        except Exception as e:
            self.finished.emit([str(e)])
        finally:
            self._is_running = False