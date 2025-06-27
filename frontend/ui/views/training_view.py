from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,QLineEdit,
                               QLabel, QPushButton, QComboBox, QProgressBar, 
                               QTableWidget, QTableWidgetItem, QFileDialog,
                               QMessageBox, QScrollArea, QApplication,
                               QGroupBox, QSizePolicy, QCheckBox)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QFont, QIcon, QColor
from ui.utils.EFFProcessor import EFFProcessor
from ui.widgets.EFFUploadDialog import EFFUploadDialog
from ui.utils.AsyncWorker import AsyncWorker
from datetime import datetime
import asyncio
import traceback
import numpy as np
from scipy import stats
import pickle
import os

import logging
from PySide6.QtCore import QThread, Signal

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class DistributionComparator:
    """Compares distributions between new data and reference data"""
    
    def __init__(self, model_path='models/my_distribution_model.pkl'):
        self.model_path = model_path
        self.model = self._load_model()
    
    def _load_model(self):
        """Load the distribution model"""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            logger.error(f"Error loading model: {e}")
        return None
    
    def calculate_confidence(self, new_data, reference_data):
        """Calculate confidence score between distributions"""
        try:
            # Extract numerical features from both datasets
            new_features = self._extract_features(new_data)
            ref_features = self._extract_features(reference_data)
            
            # Use Kolmogorov-Smirnov test for distribution comparison
            ks_statistic, p_value = stats.ks_2samp(new_features, ref_features)
            
            # Convert to confidence percentage (higher p-value = more similar)
            confidence = min(p_value * 100, 100)
            
            return confidence
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return 0
    
    def _extract_features(self, data):
        """Extract numerical features from data"""
        # This should be adapted based on your data structure
        features = []
        for item in data:
            # Example: extract test values or other numerical features
            if isinstance(item, dict) and 'value' in item:
                features.append(float(item['value']))
        return np.array(features)
    
    def find_best_match(self, new_data_metadata, all_reference_data):
        """Find best matching reference data"""
        insertion = new_data_metadata.get('insertion', '')
        product = new_data_metadata.get('product', '')
        
        # Filter by same insertion (required)
        candidates = [
            ref for ref in all_reference_data 
            if ref.get('insertion', '').lower() == insertion.lower()
        ]
        
        if not candidates:
            return None, 0
        
        # Prefer same product
        same_product = [
            ref for ref in candidates 
            if ref.get('product', '').lower() == product.lower()
        ]
        
        if same_product:
            return same_product[0], 100  # Perfect match
        
        # Return first candidate with same insertion
        return candidates[0], 80  # Good match


class ModelVersionManager:
    """Manages model versioning"""
    
    def __init__(self, base_path='models/my_distribution_model'):
        self.base_path = base_path
        self.current_version = self._get_current_version()
    
    def _get_current_version(self):
        """Get the current model version number"""
        import re
        version = 1
        model_dir = os.path.dirname(self.base_path)
        
        if os.path.exists(model_dir):
            for filename in os.listdir(model_dir):
                match = re.match(r'my_distribution_model_v(\d+)', filename)
                if match:
                    version = max(version, int(match.group(1)))
        
        return version
    
    def create_new_version(self, model_data):
        """Create a new model version"""
        new_version = self.current_version + 1
        new_path = f"{self.base_path}_v{new_version}.pkl"
        
        with open(new_path, 'wb') as f:
            pickle.dump(model_data, f)
        
        self.current_version = new_version
        return new_path, new_version


class RetrainingTab(QWidget):
    """VAMOS Tool - Variance Analysis and Model Optimization System"""
    
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
        self.workers = []
        self.current_worker = None
        self.reference_data = []
        self.data_summary = []
        self.connection_status = "unknown"
        self.distribution_comparator = DistributionComparator()
        self.version_manager = ModelVersionManager()
        self.filters = {
            'product': '',
            'lot': '',
            'test_name': '',
            'insertion': ''
        }
        self.initUI()
        QTimer.singleShot(0, self.load_initial_data)

    def load_initial_data(self):
        self.show_loading_state()
        self.load_reference_data()

    def show_loading_state(self):
        self.add_status_message("Initializing", "Loading reference data...")
        self.addDataBtn.setEnabled(False)
        self.deleteBtn.setEnabled(False)

    def show_ready_state(self):
        self.addDataBtn.setEnabled(True)
        self.deleteBtn.setEnabled(True)

    def show_no_data_state(self):
        self.addDataBtn.setEnabled(True)
        self.deleteBtn.setEnabled(False)
        self.show_empty_data_message()

    def show_empty_data_message(self):
        self.summaryTable.setRowCount(1)
        self.summaryTable.setColumnCount(1)
        self.summaryTable.setHorizontalHeaderLabels(["Status"])
        
        message_item = QTableWidgetItem("✅ Connected to backend - No reference data found.\nClick 'Add Reference Data' to upload EFF files.")
        message_item.setFlags(Qt.ItemIsEnabled)
        message_item.setBackground(QColor("#f8f9fa"))
        self.summaryTable.setItem(0, 0, message_item)
        self.summaryTable.horizontalHeader().setStretchLastSection(True)
        self.summaryTable.resizeRowsToContents()

    def create_worker(self, coro, *args, **kwargs):
        worker = AsyncWorker(coro, *args, **kwargs)
        worker.finished.connect(lambda result: self.handle_worker_finished(worker, result))
        worker.error.connect(lambda error: self.handle_worker_error(worker, error))
        self.workers.append(worker)
        return worker

    def handle_worker_finished(self, worker, result):
        if worker in self.workers:
            self.workers.remove(worker)
        if worker.isRunning():
            worker.wait(1000)
        worker.deleteLater()

    def handle_worker_error(self, worker, error):
        if worker in self.workers:
            self.workers.remove(worker)
        if worker.isRunning():
            worker.wait(1000)
        worker.deleteLater()
        self.show_error("Operation Failed", str(error))
        self.show_connection_error()

    def show_connection_error(self):
        self.connection_status = "error"
        self.add_status_message("Connection Error", "Failed to connect to backend")
        self.show_no_data_state()

    def load_reference_data(self):
        worker = self.create_worker(self._async_load_reference_data)
        worker.finished.connect(self._update_reference_table)
        worker.start()

    async def _async_load_reference_data(self):
        from api.client import APIClient
        
        worker_api_client = None
        try:
            worker_api_client = APIClient()
            data = await worker_api_client.get_reference_data_list()
            self.connection_status = "connected"
            return data if data else []
        except Exception as e:
            self.connection_status = "error"
            logger.error(f"Error loading reference data: {str(e)}")
            return []
        finally:
            if worker_api_client:
                try:
                    await worker_api_client.close()
                except Exception as e:
                    logger.error(f"Error closing worker API client: {e}")

    def _update_reference_table(self, reference_data):
        try:
            self.reference_data = reference_data if reference_data else []
                        
            if self.connection_status == "error":
                self.add_status_message("Backend Connection", "Failed - Working in offline mode")
                self.show_connection_error_in_table()
                self.show_no_data_state()
                return
            
            if not self.reference_data:
                logger.info("Backend connected but no reference data available")
                self.add_status_message("Reference Data", "Connected - No data found, ready to upload")
                self.show_no_data_state()
                return

            self.add_status_message("Reference Data", f"Loaded {len(self.reference_data)} records successfully")
            self._update_filter_options(self.reference_data)
            self._update_data_summary()
            self.show_ready_state()

        except Exception as e:
            logger.error(f"Error updating reference table: {str(e)}")
            self.show_error("Error updating reference table", str(e))
            self.show_no_data_state()

    def _update_data_summary(self):
        if not self.reference_data:
            return

        summary_dict = {}
        for data in self.reference_data:
            product = data.get('product', 'Unknown')
            lot = data.get('lot', 'Unknown')
            insertion = data.get('insertion', 'Unknown')
            
            key = f"{product}|{lot}|{insertion}"
            if key not in summary_dict:
                summary_dict[key] = {
                    'product': product,
                    'lot': lot,
                    'insertion': insertion,
                    'test_count': 0,
                    'created_at': data.get('created_at', ''),
                    'model_version': data.get('model_version', 'v1')
                }
            summary_dict[key]['test_count'] += 1

        self.data_summary = list(summary_dict.values())
        self._populate_summary_table()

    def _populate_summary_table(self):
        self.summaryTable.setColumnCount(6)
        self.summaryTable.setHorizontalHeaderLabels([
            "Product", "Lot", "Insertion", "Test Count", "Model Version", "Created At"
        ])
        
        self.summaryTable.setRowCount(len(self.data_summary))
        for row, data in enumerate(self.data_summary):
            self.summaryTable.setItem(row, 0, QTableWidgetItem(str(data.get('product', ''))))
            self.summaryTable.setItem(row, 1, QTableWidgetItem(str(data.get('lot', ''))))
            self.summaryTable.setItem(row, 2, QTableWidgetItem(str(data.get('insertion', ''))))
            self.summaryTable.setItem(row, 3, QTableWidgetItem(str(data.get('test_count', 0))))
            self.summaryTable.setItem(row, 4, QTableWidgetItem(str(data.get('model_version', 'v1'))))
            
            created_at = data.get('created_at', '')
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    formatted_date = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    formatted_date = created_at
                self.summaryTable.setItem(row, 5, QTableWidgetItem(formatted_date))

        self.summaryTable.resizeColumnsToContents()

    def show_connection_error_in_table(self):
        self.summaryTable.setRowCount(1)
        self.summaryTable.setColumnCount(1)
        self.summaryTable.setHorizontalHeaderLabels(["Connection Status"])
        
        error_item = QTableWidgetItem("❌ Cannot connect to backend. Check your connection and try again.")
        error_item.setFlags(Qt.ItemIsEnabled)
        error_item.setBackground(QColor("#dc3545"))
        error_item.setForeground(QColor("#ffffff"))
        self.summaryTable.setItem(0, 0, error_item)

    def _update_filter_options(self, reference_data):
        if not reference_data:
            self._clear_filter_options()
            return

        products = sorted(set(str(data.get('product', '')) for data in reference_data if data.get('product')))
        lots = sorted(set(str(data.get('lot', '')) for data in reference_data if data.get('lot')))
        test_names = sorted(set(str(data.get('test_name', '')) for data in reference_data if data.get('test_name')))
        insertions = sorted(set(str(data.get('insertion', '')) for data in reference_data if data.get('insertion')))

        current_product = self.productFilter.currentText()
        current_lot = self.lotFilter.currentText()
        current_test = self.testFilter.currentText()
        current_insertion = self.insertionFilter.currentText()

        self._populate_filter_combo(self.productFilter, products, current_product)
        self._populate_filter_combo(self.lotFilter, lots, current_lot)
        self._populate_filter_combo(self.testFilter, test_names, current_test)
        self._populate_filter_combo(self.insertionFilter, insertions, current_insertion)

    def _populate_filter_combo(self, combo, items, current_value):
        combo.clear()
        combo.addItem('')
        combo.addItems(items)
        if current_value in items:
            combo.setCurrentText(current_value)

    def _clear_filter_options(self):
        for combo in [self.productFilter, self.lotFilter, self.testFilter, self.insertionFilter]:
            combo.clear()
            combo.addItem('No data available')
            combo.setEnabled(False)

    def apply_filters(self):
        if self.reference_data:
            filtered_data = self._filter_data(self.reference_data)
            # Apply filtering to summary table as needed
            pass

    def _filter_data(self, reference_data):
        if not reference_data:
            return []

        filtered_data = reference_data
        
        product_filter = self.productFilter.currentText()
        lot_filter = self.lotFilter.currentText()
        test_filter = self.testFilter.currentText()
        insertion_filter = self.insertionFilter.currentText()

        if product_filter:
            filtered_data = [d for d in filtered_data if str(d.get('product', '')).lower() == product_filter.lower()]
        if lot_filter:
            filtered_data = [d for d in filtered_data if str(d.get('lot', '')).lower() == lot_filter.lower()]
        if test_filter:
            filtered_data = [d for d in filtered_data if str(d.get('test_name', '')).lower() == test_filter.lower()]
        if insertion_filter:
            filtered_data = [d for d in filtered_data if str(d.get('insertion', '')).lower() == insertion_filter.lower()]
        
        return filtered_data

    def clear_filters(self):
        for combo in [self.productFilter, self.lotFilter, self.testFilter, self.insertionFilter]:
            combo.setCurrentText('')
        self.apply_filters()

    def check_existing_data(self, product, lot, insertion):
        for data in self.reference_data:
            if (data.get('product', '').lower() == product.lower() and
                data.get('lot', '').lower() == lot.lower() and
                data.get('insertion', '').lower() == insertion.lower()):
                return True
        return False

    def add_reference_data(self):
        dialog = EFFUploadDialog(self)
        if dialog.exec_():
            upload_data = dialog.get_data()
            
            product = upload_data.get('product', '')
            lot = upload_data.get('lot', '')
            insertion = upload_data.get('insertion', '')
            use_for_retraining = upload_data.get('use_for_retraining', False)
            
            if self.check_existing_data(product, lot, insertion):
                reply = QMessageBox.question(
                    self,
                    "Data Already Exists",
                    f"Reference data for Product: {product}, Lot: {lot}, Insertion: {insertion} already exists in the database.\n\nDo you want to update the existing data?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply == QMessageBox.No:
                    return
                
                upload_data['update_existing'] = True
            
            self.progressBar.show()
            self.progressBar.setValue(0)
            self.addDataBtn.setEnabled(False)
            
            self._cleanup_current_worker()
            
            try:
                self.current_worker = AsyncWorker(
                    run_task=self._async_process_reference_data,
                    **upload_data
                )
                self.current_worker.finished.connect(self._handle_upload_complete)
                self.current_worker.error.connect(self._handle_worker_error)
                self.current_worker.progress.connect(self._update_upload_progress)
                
                self.current_worker.setParent(self)
                self.current_worker.start()
                
            except Exception as e:
                logger.error("Error creating worker: %s", str(e))
                self._handle_worker_error(str(e))

    def delete_selected_data(self):
        current_row = self.summaryTable.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a row from the summary table to delete.")
            return

        product = self.summaryTable.item(current_row, 0).text()
        lot = self.summaryTable.item(current_row, 1).text()
        insertion = self.summaryTable.item(current_row, 2).text()

        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete all reference data for:\n\nProduct: {product}\nLot: {lot}\nInsertion: {insertion}\n\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.deleteBtn.setEnabled(False)
            
            worker = self.create_worker(self._async_delete_reference_data, 
                                      product=product, lot=lot, insertion=insertion)
            worker.finished.connect(self._handle_delete_complete)
            worker.start()

    async def _async_delete_reference_data(self, product, lot, insertion):
        from api.client import APIClient
        
        worker_api_client = None
        try:
            worker_api_client = APIClient()
            
            ids_to_delete = []
            for data in self.reference_data:
                if (data.get('product', '').lower() == product.lower() and
                    data.get('lot', '').lower() == lot.lower() and
                    data.get('insertion', '').lower() == insertion.lower()):
                    ids_to_delete.append(data.get('reference_id', ''))

            deleted_count = 0
            for ref_id in ids_to_delete:
                try:
                    await worker_api_client.delete_reference_data(ref_id)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Error deleting reference data {ref_id}: {e}")

            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting reference data: {str(e)}")
            raise
        finally:
            if worker_api_client:
                try:
                    await worker_api_client.close()
                except Exception as e:
                    logger.error(f"Error closing worker API client: {e}")

    def _handle_delete_complete(self, deleted_count):
        self.deleteBtn.setEnabled(True)
        
        if deleted_count > 0:
            self.add_status_message("Data Deletion", f"Successfully deleted {deleted_count} records")
            self.load_reference_data()
        else:
            self.add_status_message("Data Deletion", "No records were deleted")

    def _handle_worker_error(self, error_msg):
        logger.error("Worker error: %s", error_msg)
        self.show_error("Processing Error", error_msg)
        self.addDataBtn.setEnabled(True)
        self.progressBar.hide()
        self._cleanup_current_worker()

    def _cleanup_current_worker(self):
        if self.current_worker:
            try:
                if self.current_worker.isRunning():
                    self.current_worker.wait(3000)
                self.current_worker.deleteLater()
            except Exception as e:
                logger.error("Error cleaning up worker: %s", str(e))
            finally:
                self.current_worker = None

    async def _async_process_reference_data(self, file_path, product, lot, insertion, 
                                       use_for_retraining=False, update_existing=False):
        from api.client import APIClient
        
        worker_api_client = None
        try:
            worker_api_client = APIClient()
            processor = EFFProcessor(worker_api_client)
            
            
            # Process the EFF file
            eff_data = await processor.process_eff_file(file_path, product, lot, insertion)
            
            if use_for_retraining:
                try:
                    # Validate we have reference data
                    if not self.reference_data:
                        self.current_worker.progress.emit(
                            100, "VAMOS Analysis", 
                            "No reference data available for comparison"
                        )
                        logger.warning("No reference data available for VAMOS analysis")
                        return eff_data
                    
                    # Find matching reference data
                    self.current_worker.progress.emit(30, "VAMOS Analysis", "Finding matching reference data...")
                    
                    metadata = {'product': product, 'lot': lot, 'insertion': insertion}
                    best_match, match_score = self.distribution_comparator.find_best_match(
                        metadata, self.reference_data
                    )
                    
                    if best_match:
                        self.current_worker.progress.emit(50, "VAMOS Analysis", 
                                                        f"Found match with {match_score}% similarity")
                        
                        # Calculate confidence with error handling
                        try:
                            confidence = self.distribution_comparator.calculate_confidence(
                                eff_data, [best_match]
                            )
                        except Exception as e:
                            logger.error(f"Error calculating confidence: {e}")
                            self.current_worker.progress.emit(
                                100, "VAMOS Analysis", 
                                "Error in distribution analysis"
                            )
                            return eff_data
                        
                        self.current_worker.progress.emit(70, "VAMOS Analysis", 
                                                        f"Distribution confidence: {confidence:.1f}%")
                        
                        if confidence >= 95:
                            # Trigger automatic retraining
                            self.current_worker.progress.emit(80, "Model Training", 
                                                            "High confidence detected - Starting automatic retraining...")
                            
                            # Prepare training data with proper format
                            training_data = {
                                'reference_id': best_match.get('reference_id', ''),
                                'reference_data': [best_match],  # Include reference data
                                'new_data': eff_data,  # Include new data
                                'confidence': confidence,
                                'insertion': insertion,
                                'product': product,
                                'lot': lot,
                                'automatic': True,
                                'user': 'VAMOS',
                                'version': self.version_manager.current_version
                            }
                            
                            try:
                                # Perform retraining
                                retrain_result = await worker_api_client.retrain_model_with_data(training_data)
                                
                                if retrain_result.get('status') == 'completed':
                                    # Create new model version
                                    new_version = retrain_result.get('version', f'v{self.version_manager.current_version + 1}')
                                    
                                    self.current_worker.progress.emit(90, "Model Training", 
                                                                    f"Created model version {new_version}")
                                    
                                    # Update metrics
                                    await worker_api_client.update_model_metrics({
                                        'version': new_version,
                                        'confidence': confidence,
                                        'accuracy': retrain_result.get('metrics', {}).get('accuracy', 0),
                                        'training_data': metadata
                                    })
                                    
                                    # Mark reference data as used for training
                                    if best_match.get('reference_id'):
                                        await worker_api_client.update_reference_data(
                                            best_match['reference_id'],
                                            {
                                                'used_for_training': True,
                                                'training_version': new_version,
                                                'quality_score': confidence
                                            }
                                        )
                                    
                                    # Update local version manager
                                    version_num = int(new_version[1:]) if new_version.startswith('v') else 2
                                    self.version_manager.current_version = version_num
                                    
                                    self.current_worker.progress.emit(100, "VAMOS Analysis", 
                                                                    f"Training completed successfully - Model {new_version} created")
                                else:
                                    error_msg = retrain_result.get('message', 'Unknown error')
                                    self.current_worker.progress.emit(100, "Model Training", 
                                                                    f"Training failed: {error_msg}")
                                    
                            except Exception as e:
                                logger.error(f"Error during model retraining: {e}")
                                self.current_worker.progress.emit(100, "Model Training", 
                                                                f"Training error: {str(e)}")
                        else:
                            self.current_worker.progress.emit(100, "VAMOS Analysis", 
                                                            f"Confidence too low ({confidence:.1f}%) - Manual review required")
                    else:
                        self.current_worker.progress.emit(100, "VAMOS Analysis", 
                                                        "No matching reference data found with same insertion")
                except Exception as e:
                    logger.error(f"Error in VAMOS analysis: {e}", exc_info=True)
                    self.current_worker.progress.emit(100, "VAMOS Analysis", 
                                                    f"Analysis error: {str(e)}")
            
            return eff_data
            
        except Exception as e:
            logger.error("Error processing data: %s", str(e), exc_info=True)
            raise
        finally:
            if worker_api_client:
                try:
                    await worker_api_client.close()
                except Exception as e:
                    logger.error(f"Error closing worker API client: {e}")

    def _update_upload_progress(self, value, event, status):
        self.progressBar.setValue(value)
        self.add_status_message(event, status)

    def _handle_upload_complete(self, result):
        self.addDataBtn.setEnabled(True)
        self.progressBar.hide()
        if result:
            self.add_status_message("Upload completed", "Success")
            self.load_reference_data()
        else:
            self.add_status_message("Upload failed", "Error")
        self._cleanup_current_worker()

    def add_status_message(self, event: str, status: str):
        current_time = datetime.now().strftime("%H:%M:%S")
        row_position = self.statusTable.rowCount()
        self.statusTable.insertRow(row_position)
        
        self.statusTable.setItem(row_position, 0, QTableWidgetItem(current_time))
        self.statusTable.setItem(row_position, 1, QTableWidgetItem(event))
        self.statusTable.setItem(row_position, 2, QTableWidgetItem(status))
        
        self.statusTable.scrollToBottom()

    def show_error(self, title: str, message: str):
        QMessageBox.critical(self, title, str(message))
        self.add_status_message(f"Error: {title}", "Failed")
        print(f"Error: {title}\n{message}")

    def closeEvent(self, event):        
        self._cleanup_current_worker()
        
        for worker in self.workers[:]:
            try:
                if worker.isRunning():
                    worker.wait(2000)
                worker.deleteLater()
            except Exception as e:
                logger.error(f"Error stopping worker: {str(e)}")
        self.workers.clear()
        
        try:
            import threading
            
            def close_main_api_client():
                try:
                    cleanup_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(cleanup_loop)
                    cleanup_loop.run_until_complete(self.api_client.close())
                    cleanup_loop.close()
                except Exception as e:
                    logger.error("Error during main API client cleanup: %s", str(e))
            
            cleanup_thread = threading.Thread(target=close_main_api_client)
            cleanup_thread.start()
            cleanup_thread.join(timeout=1.0)
            
        except Exception as e:
            logger.error("Error during cleanup thread: %s", str(e))
        
        event.accept()

    def initUI(self):
        self.setStyleSheet("background-color: white; color: black")
        
        # Main layout
        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(40, 40, 40, 40)
        mainLayout.setSpacing(15)
        
        # Action buttons section
        buttonsLayout = QHBoxLayout()
        
        self.addDataBtn = QPushButton("📁 Add Reference Data")
        self.addDataBtn.setStyleSheet("""
            QPushButton {
                background-color: #1849D6;
                color: white;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
                margin-right: 10px;
            }
            QPushButton:hover {
                background-color: #0f3bb3;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        self.addDataBtn.clicked.connect(self.add_reference_data)
        
        self.deleteBtn = QPushButton("🗑️ Delete Selected")
        self.deleteBtn.setStyleSheet("""
            QPushButton {
                background-color: #FF0000;
                color: white;
                border-radius: 5px;
                padding: 8px 15px;
                font-weight: bold;
                margin-right: 10px;
            }
            QPushButton:hover {
                background-color: #CC0000;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        self.deleteBtn.clicked.connect(self.delete_selected_data)
        
        buttonsLayout.addWidget(self.addDataBtn)
        buttonsLayout.addWidget(self.deleteBtn)
        buttonsLayout.addStretch()
        
        # VAMOS Status Indicator
        self.vamos_status = QLabel("🔍 VAMOS: Ready")
        self.vamos_status.setStyleSheet("""
            QLabel {
                background-color: #28a745;
                color: white;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        buttonsLayout.addWidget(self.vamos_status)
        
        mainLayout.addLayout(buttonsLayout)

        # Progress bar
        self.progressBar = QProgressBar()
        self.progressBar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #CCCCCC;
                border-radius: 5px;
                text-align: center;
                height: 25px;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #1849D6;
                border-radius: 3px;
            }
        """)
        self.progressBar.setValue(0)
        self.progressBar.hide()
        mainLayout.addWidget(self.progressBar)

        # Filter section
        filterLabel = QLabel("Data Filters")
        filterLabel.setFont(QFont("Arial", 10, QFont.Bold))
        filterLabel.setStyleSheet("margin-top: 10px; margin-bottom: 5px;")
        mainLayout.addWidget(filterLabel)
        
        filterRowLayout = QHBoxLayout()
        
        filter_style = """
            QComboBox {
                padding: 6px;
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                background-color: white;
                min-width: 80px;
            }
            QComboBox:focus {
                border-color: #1849D6;
            }
        """
        
        self.productFilter = QComboBox()
        self.productFilter.setEditable(True)
        self.productFilter.setStyleSheet(filter_style)
        self.productFilter.currentTextChanged.connect(lambda: self.apply_filters())
        
        self.lotFilter = QComboBox()
        self.lotFilter.setEditable(True)
        self.lotFilter.setStyleSheet(filter_style)
        self.lotFilter.currentTextChanged.connect(lambda: self.apply_filters())
        
        self.testFilter = QComboBox()
        self.testFilter.setEditable(True)
        self.testFilter.setStyleSheet(filter_style)
        self.testFilter.currentTextChanged.connect(lambda: self.apply_filters())
        
        self.insertionFilter = QComboBox()
        self.insertionFilter.setEditable(True)
        self.insertionFilter.setStyleSheet(filter_style)
        self.insertionFilter.currentTextChanged.connect(lambda: self.apply_filters())
        
        self.clearFiltersBtn = QPushButton("Clear")
        self.clearFiltersBtn.clicked.connect(self.clear_filters)
        self.clearFiltersBtn.setStyleSheet("""
            QPushButton {
                background-color: #FFA500;
                color: white;
                padding: 6px 12px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e68a00;
            }
        """)
        
        filterRowLayout.addWidget(QLabel("Product:"))
        filterRowLayout.addWidget(self.productFilter)
        filterRowLayout.addWidget(QLabel("Lot:"))
        filterRowLayout.addWidget(self.lotFilter)
        filterRowLayout.addWidget(QLabel("Test:"))
        filterRowLayout.addWidget(self.testFilter)
        filterRowLayout.addWidget(QLabel("Insertion:"))
        filterRowLayout.addWidget(self.insertionFilter)
        filterRowLayout.addWidget(self.clearFiltersBtn)
        filterRowLayout.addStretch()
        
        mainLayout.addLayout(filterRowLayout)

        # Data summary table
        summaryLabel = QLabel("📊 Reference Data Summary")
        summaryLabel.setFont(QFont("Arial", 10, QFont.Bold))
        summaryLabel.setStyleSheet("color: black; margin-top: 15px; margin-bottom: 10px;")
        mainLayout.addWidget(summaryLabel)

        self.summaryTable = QTableWidget()
        self.summaryTable.setStyleSheet("""
            QTableWidget {
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                gridline-color: #f0f0f0;
                background-color: white;
                selection-background-color: #1849D6;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                color: black;
                padding: 8px;
                border: 1px solid #CCCCCC;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #1849D6;
                color: white;
            }
        """)
        self.summaryTable.setSelectionBehavior(QTableWidget.SelectRows)
        self.summaryTable.setAlternatingRowColors(True)
        self.summaryTable.horizontalHeader().setStretchLastSection(True)
        self.summaryTable.setMinimumHeight(200)
        mainLayout.addWidget(self.summaryTable)

        # Status messages section
        statusLabel = QLabel("📋 VAMOS Operation Log")
        statusLabel.setFont(QFont("Arial", 10, QFont.Bold))
        statusLabel.setStyleSheet("color: black; margin-top: 15px; margin-bottom: 10px;")
        mainLayout.addWidget(statusLabel)

        self.statusTable = QTableWidget()
        self.statusTable.setColumnCount(3)
        self.statusTable.setHorizontalHeaderLabels(["Time", "Event", "Status"])
        self.statusTable.setMaximumHeight(150)
        self.statusTable.setStyleSheet("""
            QTableWidget {
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                gridline-color: #f0f0f0;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                color: black;
                padding: 6px;
                border: 1px solid #CCCCCC;
                font-weight: bold;
                font-size: 9px;
            }
            QTableWidget::item {
                padding: 4px;
                border-bottom: 1px solid #f0f0f0;
                font-size: 9px;
            }
        """)
        self.statusTable.horizontalHeader().setStretchLastSection(True)
        self.statusTable.setSelectionBehavior(QTableWidget.SelectRows)
        mainLayout.addWidget(self.statusTable)

        # Add stretch to push everything up
        mainLayout.addStretch()


class EFFUploadDialog(QWidget):
    """Extended EFF Upload Dialog with VAMOS retraining option"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowFlags(Qt.Dialog)
        self.data = {}
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle("Add Reference Data - VAMOS")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Upload EFF File for Reference Data")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # File selection
        file_frame = QFrame()
        file_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 2px dashed #1849D6;
                border-radius: 8px;
                padding: 20px;
            }
        """)
        file_layout = QVBoxLayout(file_frame)
        
        self.file_label = QLabel("No file selected")
        self.file_label.setAlignment(Qt.AlignCenter)
        file_layout.addWidget(self.file_label)
        
        select_btn = QPushButton("Choose EFF File")
        select_btn.clicked.connect(self.select_file)
        file_layout.addWidget(select_btn)
        
        layout.addWidget(file_frame)
        
        # Input fields
        form_layout = QVBoxLayout()
        
        self.product_input = self.create_input_field("Product:")
        self.lot_input = self.create_input_field("Lot:")
        self.insertion_input = self.create_input_field("Insertion:")
        
        form_layout.addWidget(self.product_input[0])
        form_layout.addWidget(self.product_input[1])
        form_layout.addWidget(self.lot_input[0])
        form_layout.addWidget(self.lot_input[1])
        form_layout.addWidget(self.insertion_input[0])
        form_layout.addWidget(self.insertion_input[1])
        
        layout.addLayout(form_layout)
        
        # VAMOS Retraining checkbox
        self.retrain_checkbox = QCheckBox("Use this data for automatic retraining (VAMOS)")
        self.retrain_checkbox.setStyleSheet("""
            QCheckBox {
                font-weight: bold;
                color: #1849D6;
                padding: 10px;
                background-color: #e3f2fd;
                border-radius: 5px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
        """)
        layout.addWidget(self.retrain_checkbox)
        
        # Info label
        info_label = QLabel("ℹ️ If checked, VAMOS will analyze distribution similarity and automatically retrain if confidence ≥ 95%")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666666; font-size: 11px; padding: 5px;")
        layout.addWidget(info_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        self.upload_btn = QPushButton("Upload")
        self.upload_btn.clicked.connect(self.accept)
        self.upload_btn.setEnabled(False)
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #1849D6;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0f3bb3;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(self.upload_btn)
        
        layout.addLayout(button_layout)
    
    def create_input_field(self, label_text):
        label = QLabel(label_text)
        label.setFont(QFont("Arial", 10))
        
        input_field = QLineEdit()
        input_field.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #1849D6;
            }
        """)
        input_field.textChanged.connect(self.validate_inputs)
        
        return label, input_field
    
    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select EFF File",
            "",
            "EFF Files (*.eff);;All Files (*)"
        )
        
        if file_path:
            self.data['file_path'] = file_path
            self.file_label.setText(os.path.basename(file_path))
            self.validate_inputs()
    
    def validate_inputs(self):
        has_file = 'file_path' in self.data
        has_product = bool(self.product_input[1].text().strip())
        has_lot = bool(self.lot_input[1].text().strip())
        has_insertion = bool(self.insertion_input[1].text().strip())
        
        self.upload_btn.setEnabled(has_file and has_product and has_lot and has_insertion)
    
    def accept(self):
        self.data['product'] = self.product_input[1].text().strip()
        self.data['lot'] = self.lot_input[1].text().strip()
        self.data['insertion'] = self.insertion_input[1].text().strip()
        self.data['use_for_retraining'] = self.retrain_checkbox.isChecked()
        self.close()
        self.parent.dialog_result = True
    
    def reject(self):
        self.close()
        self.parent.dialog_result = False
    
    def exec_(self):
        self.parent.dialog_result = False
        self.show()
        while self.isVisible():
            QApplication.processEvents()
        return self.parent.dialog_result
    
    def get_data(self):
        return self.data