from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                               QLabel, QPushButton, QComboBox, QProgressBar, 
                               QTableWidget, QTableWidgetItem, QFileDialog,
                               QMessageBox, QTabWidget, QSplitter, QHeaderView,
                               QGroupBox, QGridLayout, QSpacerItem, QSizePolicy,
                               QScrollArea, QApplication)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QFont, QIcon, QColor
from ui.utils.EFFProcessor import EFFProcessor
from ui.widgets.EFFUploadDialog import EFFUploadDialog
from datetime import datetime
import asyncio
import traceback

import logging
from PySide6.QtCore import QThread, Signal

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class AsyncWorker(QThread):
    finished = Signal(object)
    error = Signal(str)
    progress = Signal(int, str, str)

    def __init__(self, run_task, **kwargs):
        super().__init__()
        self.run_task = run_task
        self.kwargs = kwargs
        self._is_running = False
        self._loop = None
        self._task = None
        logger.debug("AsyncWorker initialized with kwargs: %s", kwargs)

    def run(self):
        try:
            logger.debug("AsyncWorker starting run")
            self._is_running = True
            
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            
            result = self._loop.run_until_complete(self._safe_run_task())
            
            logger.debug("Task completed with result: %s", result)
            self.finished.emit(result)

        except Exception as e:
            logger.error("Error in worker: %s", str(e), exc_info=True)
            self.error.emit(str(e))
        finally:
            self._cleanup()

    async def _safe_run_task(self):
        try:
            self._task = asyncio.create_task(self.run_task(**self.kwargs))
            return await self._task
        except asyncio.CancelledError:
            logger.debug("Task was cancelled")
            raise Exception("Operation cancelled")
        except Exception as e:
            logger.error(f"Task execution error: {str(e)}")
            raise
        finally:
            pass

    def _cleanup(self):
        logger.debug("Starting worker cleanup")
        try:
            if self._loop and not self._loop.is_closed():
                pending_tasks = list(asyncio.all_tasks(self._loop))
                
                if pending_tasks:
                    for task in pending_tasks:
                        if not task.done():
                            task.cancel()
                    
                    try:
                        self._loop.run_until_complete(
                            asyncio.wait_for(
                                asyncio.gather(*pending_tasks, return_exceptions=True),
                                timeout=2.0
                            )
                        )
                    except (asyncio.TimeoutError, Exception) as e:
                        logger.debug(f"Task cleanup timeout or error: {e}")
                
                if not self._loop.is_closed():
                    self._loop.close()
        except Exception as e:
            logger.error("Error during cleanup: %s", str(e))
        finally:
            self._loop = None
            self._task = None
            self._is_running = False
            logger.debug("Worker cleanup completed")

    def stop(self):
        logger.debug("Stopping worker")
        if self._is_running and self._loop and not self._loop.is_closed():
            try:
                self._loop.call_soon_threadsafe(self._cancel_task)
            except Exception as e:
                logger.error("Error cancelling task: %s", str(e))
        self.wait()
        logger.debug("Worker stopped")
    
    def _cancel_task(self):
        if self._task and not self._task.done():
            self._task.cancel()

class RetrainingTab(QWidget):
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
        self.workers = []
        self.current_worker = None
        self.reference_data = []
        self.data_summary = []
        self.connection_status = "unknown"
        self.filters = {
            'product': '',
            'lot': '',
            'test_name': '',
            'insertion': ''
        }
        self.initUI()
        QTimer.singleShot(0, self.load_initial_data)

    def load_initial_data(self):
        logger.debug("Starting initial data load")
        self.show_loading_state()
        self.load_reference_data()

    def show_loading_state(self):
        self.add_status_message("Initializing", "Loading reference data...")
        self.addDataBtn.setEnabled(False)
        self.retrainBtn.setEnabled(False)
        self.deleteBtn.setEnabled(False)
        self.set_loading_overlay("Loading data...")

    def show_ready_state(self):
        self.addDataBtn.setEnabled(True)
        self.retrainBtn.setEnabled(True)
        self.deleteBtn.setEnabled(True)
        self.hide_loading_overlay()

    def show_no_data_state(self):
        self.addDataBtn.setEnabled(True)
        self.retrainBtn.setEnabled(False)
        self.deleteBtn.setEnabled(False)
        self.hide_loading_overlay()
        self.show_empty_data_message()

    def set_loading_overlay(self, message="Processing..."):
        self.loadingLabel.setText(f"⏳ {message}")
        self.loadingLabel.show()
        QApplication.processEvents()

    def hide_loading_overlay(self):
        self.loadingLabel.hide()
        QApplication.processEvents()

    def show_empty_data_message(self):
        self.referenceTable.setRowCount(1)
        self.referenceTable.setColumnCount(1)
        self.referenceTable.setHorizontalHeaderLabels(["Status"])
        
        message_item = QTableWidgetItem("✅ Connected to backend - No reference data found.\nClick 'Add Reference Data' to upload EFF files and start training.")
        message_item.setFlags(Qt.ItemIsEnabled)
        message_item.setBackground(QColor("#f8f9fa"))
        self.referenceTable.setItem(0, 0, message_item)
        self.referenceTable.horizontalHeader().setStretchLastSection(True)
        self.referenceTable.resizeRowsToContents()

        self.summaryTable.setRowCount(1)
        self.summaryTable.setColumnCount(1)
        self.summaryTable.setHorizontalHeaderLabels(["Status"])
        summary_item = QTableWidgetItem("No data available")
        summary_item.setFlags(Qt.ItemIsEnabled)
        summary_item.setBackground(QColor("#f8f9fa"))
        self.summaryTable.setItem(0, 0, summary_item)

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
            logger.debug(f"Loaded reference data: {len(data) if data else 0} records")
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
            
            logger.debug(f"Processing reference data: {len(self.reference_data)} records")
            
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
            filtered_data = self._filter_data(self.reference_data)
            self._populate_table_with_data(filtered_data)
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
                    'created_at': data.get('created_at', '')
                }
            summary_dict[key]['test_count'] += 1

        self.data_summary = list(summary_dict.values())
        self._populate_summary_table()

    def _populate_summary_table(self):
        self.summaryTable.setColumnCount(5)
        self.summaryTable.setHorizontalHeaderLabels([
            "Product", "Lot", "Insertion", "Test Count", "Created At"
        ])
        
        self.summaryTable.setRowCount(len(self.data_summary))
        for row, data in enumerate(self.data_summary):
            self.summaryTable.setItem(row, 0, QTableWidgetItem(str(data.get('product', ''))))
            self.summaryTable.setItem(row, 1, QTableWidgetItem(str(data.get('lot', ''))))
            self.summaryTable.setItem(row, 2, QTableWidgetItem(str(data.get('insertion', ''))))
            self.summaryTable.setItem(row, 3, QTableWidgetItem(str(data.get('test_count', 0))))
            
            created_at = data.get('created_at', '')
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    formatted_date = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    formatted_date = created_at
                self.summaryTable.setItem(row, 4, QTableWidgetItem(formatted_date))

        self.summaryTable.resizeColumnsToContents()

    def show_connection_error_in_table(self):
        self.referenceTable.setRowCount(1)
        self.referenceTable.setColumnCount(1)
        self.referenceTable.setHorizontalHeaderLabels(["Connection Status"])
        
        error_item = QTableWidgetItem("❌ Cannot connect to backend. Check your connection and try again.")
        error_item.setFlags(Qt.ItemIsEnabled)
        error_item.setBackground(QColor("#dc3545"))
        error_item.setForeground(QColor("#ffffff"))
        self.referenceTable.setItem(0, 0, error_item)

    def _populate_table_with_data(self, filtered_data):
        self.referenceTable.setColumnCount(8)
        self.referenceTable.setHorizontalHeaderLabels([
            "Product", "Lot", "Insertion", "Test Name", 
            "Test Number", "LSL", "USL", "Created At"
        ])
        
        self.referenceTable.setRowCount(len(filtered_data))
        for row, data in enumerate(filtered_data):
            self.referenceTable.setItem(row, 0, QTableWidgetItem(str(data.get('product', ''))))
            self.referenceTable.setItem(row, 1, QTableWidgetItem(str(data.get('lot', ''))))
            self.referenceTable.setItem(row, 2, QTableWidgetItem(str(data.get('insertion', ''))))
            self.referenceTable.setItem(row, 3, QTableWidgetItem(str(data.get('test_name', ''))))
            self.referenceTable.setItem(row, 4, QTableWidgetItem(str(data.get('test_number', ''))))
            self.referenceTable.setItem(row, 5, QTableWidgetItem(str(data.get('lsl', ''))))
            self.referenceTable.setItem(row, 6, QTableWidgetItem(str(data.get('usl', ''))))
            
            created_at = data.get('created_at', '')
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    formatted_date = created_at
                self.referenceTable.setItem(row, 7, QTableWidgetItem(formatted_date))

        self.referenceTable.resizeColumnsToContents()
        logger.debug(f"Updated reference table with {self.referenceTable.rowCount()} rows")

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

    def apply_filters(self):
        if self.reference_data:
            filtered_data = self._filter_data(self.reference_data)
            self._populate_table_with_data(filtered_data)

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
            logger.debug("Upload data received: %s", upload_data)
            
            product = upload_data.get('product', '')
            lot = upload_data.get('lot', '')
            insertion = upload_data.get('insertion', '')
            
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
            
            self.set_loading_overlay("Processing EFF file...")
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
                logger.debug("New worker started")
                
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
            self.set_loading_overlay("Deleting data...")
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
        self.hide_loading_overlay()
        
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
            logger.debug("Cleaning up current worker")
            try:
                if self.current_worker.isRunning():
                    self.current_worker.wait(3000)
                self.current_worker.deleteLater()
            except Exception as e:
                logger.error("Error cleaning up worker: %s", str(e))
            finally:
                self.current_worker = None

    async def _async_process_reference_data(self, file_path, product, lot, insertion, update_existing=False):
        from api.client import APIClient
        
        worker_api_client = None
        try:
            worker_api_client = APIClient()
            processor = EFFProcessor(worker_api_client)
            
            logger.debug(f"Processing EFF file: {file_path} (update_existing: {update_existing})")
            result = await processor.process_eff_file(file_path, product, lot, insertion)
            logger.debug(f"Processing completed successfully")
            return result
            
        except Exception as e:
            logger.error("Error processing data: %s", str(e), exc_info=True)
            raise
        finally:
            if worker_api_client:
                try:
                    await worker_api_client.close()
                    logger.debug("Worker API client closed successfully")
                except Exception as e:
                    logger.error(f"Error closing worker API client: {e}")

    def _update_upload_progress(self, value, event, status):
        self.progressBar.setValue(value)
        self.add_status_message(event, status)

    def _handle_upload_complete(self, result):
        logger.debug("Upload completed with result: %s", result)
        self.addDataBtn.setEnabled(True)
        self.progressBar.hide()
        if result:
            self.add_status_message("Upload completed", "Success")
            self.load_reference_data()
        else:
            self.add_status_message("Upload failed", "Error")
        self._cleanup_current_worker()

    def start_retraining(self):
        if not self.reference_data:
            QMessageBox.warning(
                self, 
                "No Reference Data", 
                "Cannot start retraining without reference data. Please upload reference data first."
            )
            return

        self.retrainBtn.setEnabled(False)
        worker = self.create_worker(self._async_start_retraining)
        worker.progress.connect(self._update_training_progress)
        worker.finished.connect(lambda _: self._handle_training_complete())
        worker.start()

    async def _async_start_retraining(self):
        from api.client import APIClient
        
        worker_api_client = None
        try:
            worker_api_client = APIClient()
            await worker_api_client.start_model_retraining()
            return True
        except Exception as e:
            logger.error(f"Error starting retraining: {str(e)}")
            raise
        finally:
            if worker_api_client:
                try:
                    await worker_api_client.close()
                except Exception as e:
                    logger.error(f"Error closing worker API client: {e}")

    def _update_training_progress(self, value, event, status):
        self.progressBar.setValue(value)
        self.add_status_message(event, status)

    def _handle_training_complete(self):
        self.retrainBtn.setEnabled(True)
        self.progressBar.hide()
        self.add_status_message("Training completed", "Success")

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
        logger.debug("Closing RetrainingTab")
        
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
        # Create main scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Create main content widget
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # Loading overlay label
        self.loadingLabel = QLabel("⏳ Loading...")
        self.loadingLabel.setAlignment(Qt.AlignCenter)
        self.loadingLabel.setStyleSheet("""
            QLabel {
                background-color: rgba(52, 73, 94, 0.9);
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 20px;
                border-radius: 10px;
                margin: 10px;
            }
        """)
        self.loadingLabel.hide()
        controlPanel = QGroupBox("Training Controls")
        controlPanel.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        controlLayout = QHBoxLayout(controlPanel)

        self.addDataBtn = QPushButton("📁 Add Reference Data")
        self.addDataBtn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 12px 20px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.addDataBtn.clicked.connect(self.add_reference_data)
        controlLayout.addWidget(self.addDataBtn)

        self.deleteBtn = QPushButton("🗑️ Delete Selected")
        self.deleteBtn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 12px 20px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.deleteBtn.clicked.connect(self.delete_selected_data)
        controlLayout.addWidget(self.deleteBtn)

        self.retrainBtn = QPushButton("🚀 Start Retraining")
        self.retrainBtn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 12px 20px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.retrainBtn.clicked.connect(self.start_retraining)
        controlLayout.addWidget(self.retrainBtn)

        controlLayout.addStretch()

        scheduleGroup = QVBoxLayout()
        scheduleLabel = QLabel("Schedule:")
        scheduleLabel.setStyleSheet("font-weight: bold; color: #34495e;")
        self.scheduleCombo = QComboBox()
        self.scheduleCombo.addItems(["Manual", "Daily", "Weekly", "Monthly"])
        self.scheduleCombo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                background-color: white;
                min-width: 120px;
            }
            QComboBox:focus {
                border-color: #3498db;
            }
        """)
        scheduleGroup.addWidget(scheduleLabel)
        scheduleGroup.addWidget(self.scheduleCombo)
        controlLayout.addLayout(scheduleGroup)

        layout.addWidget(controlPanel)

        progressFrame = QGroupBox("Processing Progress")
        progressFrame.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        progressLayout = QVBoxLayout(progressFrame)

        self.progressBar = QProgressBar()
        self.progressBar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                text-align: center;
                height: 25px;
                background-color: #ecf0f1;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 6px;
            }
        """)
        self.progressBar.setValue(0)
        self.progressBar.hide()
        progressLayout.addWidget(self.progressBar)

        layout.addWidget(progressFrame)

        filterFrame = QGroupBox("Data Filters")
        filterFrame.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        filterLayout = QGridLayout(filterFrame)

        filter_style = """
            QComboBox {
                padding: 6px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                background-color: white;
                min-width: 120px;
            }
            QComboBox:focus {
                border-color: #3498db;
            }
        """

        productLabel = QLabel("Product:")
        productLabel.setStyleSheet("font-weight: bold; color: #34495e;")
        self.productFilter = QComboBox()
        self.productFilter.setEditable(True)
        self.productFilter.setStyleSheet(filter_style)
        self.productFilter.currentTextChanged.connect(lambda: self.apply_filters())
        filterLayout.addWidget(productLabel, 0, 0)
        filterLayout.addWidget(self.productFilter, 0, 1)

        lotLabel = QLabel("Lot:")
        lotLabel.setStyleSheet("font-weight: bold; color: #34495e;")
        self.lotFilter = QComboBox()
        self.lotFilter.setEditable(True)
        self.lotFilter.setStyleSheet(filter_style)
        self.lotFilter.currentTextChanged.connect(lambda: self.apply_filters())
        filterLayout.addWidget(lotLabel, 0, 2)
        filterLayout.addWidget(self.lotFilter, 0, 3)

        testLabel = QLabel("Test Name:")
        testLabel.setStyleSheet("font-weight: bold; color: #34495e;")
        self.testFilter = QComboBox()
        self.testFilter.setEditable(True)
        self.testFilter.setStyleSheet(filter_style)
        self.testFilter.currentTextChanged.connect(lambda: self.apply_filters())
        filterLayout.addWidget(testLabel, 1, 0)
        filterLayout.addWidget(self.testFilter, 1, 1)

        insertionLabel = QLabel("Insertion:")
        insertionLabel.setStyleSheet("font-weight: bold; color: #34495e;")
        self.insertionFilter = QComboBox()
        self.insertionFilter.setEditable(True)
        self.insertionFilter.setStyleSheet(filter_style)
        self.insertionFilter.currentTextChanged.connect(lambda: self.apply_filters())
        filterLayout.addWidget(insertionLabel, 1, 2)
        filterLayout.addWidget(self.insertionFilter, 1, 3)

        self.clearFiltersBtn = QPushButton("Clear All Filters")
        self.clearFiltersBtn.clicked.connect(self.clear_filters)
        self.clearFiltersBtn.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        filterLayout.addWidget(self.clearFiltersBtn, 1, 4)

        layout.addWidget(filterFrame)

        dataTabWidget = QTabWidget()
        dataTabWidget.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #ecf0f1;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #3498db;
                color: white;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background-color: #d5dbdb;
            }
        """)

        summaryWidget = QWidget()
        summaryLayout = QVBoxLayout(summaryWidget)

        summaryLabel = QLabel("📊 Data Summary by Product/Lot/Insertion")
        summaryLabel.setFont(QFont("Arial", 12, QFont.Bold))
        summaryLabel.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        summaryLayout.addWidget(summaryLabel)

        self.summaryTable = QTableWidget()
        self.summaryTable.setStyleSheet("""
            QTableWidget {
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                gridline-color: #ecf0f1;
                background-color: white;
                selection-background-color: #3498db;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 8px;
                border: 1px solid #2c3e50;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #ecf0f1;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        self.summaryTable.setSelectionBehavior(QTableWidget.SelectRows)
        self.summaryTable.setAlternatingRowColors(True)
        self.summaryTable.horizontalHeader().setStretchLastSection(True)
        summaryLayout.addWidget(self.summaryTable)

        detailWidget = QWidget()
        detailLayout = QVBoxLayout(detailWidget)

        detailLabel = QLabel("📋 Detailed Reference Data")
        detailLabel.setFont(QFont("Arial", 12, QFont.Bold))
        detailLabel.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        detailLayout.addWidget(detailLabel)

        self.referenceTable = QTableWidget()
        self.referenceTable.setStyleSheet("""
            QTableWidget {
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                gridline-color: #ecf0f1;
                background-color: white;
                selection-background-color: #3498db;
            }
            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 8px;
                border: 1px solid #2c3e50;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #ecf0f1;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        self.referenceTable.setSelectionBehavior(QTableWidget.SelectRows)
        self.referenceTable.setAlternatingRowColors(True)
        self.referenceTable.horizontalHeader().setStretchLastSection(True)
        detailLayout.addWidget(self.referenceTable)

        dataTabWidget.addTab(summaryWidget, "📊 Summary")
        dataTabWidget.addTab(detailWidget, "📋 Details")

        layout.addWidget(dataTabWidget)

        statusFrame = QGroupBox("Operation Status")
        statusFrame.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        statusLayout = QVBoxLayout(statusFrame)

        self.statusTable = QTableWidget()
        self.statusTable.setColumnCount(3)
        self.statusTable.setHorizontalHeaderLabels(["Time", "Event", "Status"])
        self.statusTable.setMaximumHeight(150)
        self.statusTable.setStyleSheet("""
            QTableWidget {
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                gridline-color: #ecf0f1;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #95a5a6;
                color: white;
                padding: 6px;
                border: 1px solid #7f8c8d;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #ecf0f1;
            }
        """)
        self.statusTable.horizontalHeader().setStretchLastSection(True)
        self.statusTable.setSelectionBehavior(QTableWidget.SelectRows)
        self.statusTable.setAlternatingRowColors(True)
        statusLayout.addWidget(self.statusTable)

        layout.addWidget(statusFrame)

        # Set the content widget to the scroll area
        scroll_area.setWidget(content_widget)
        
        # Create the main layout for the widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)
        
        # Add loading overlay on top
        overlay_layout = QVBoxLayout()
        overlay_layout.addWidget(self.loadingLabel, alignment=Qt.AlignCenter)
        main_layout.addLayout(overlay_layout)

        self.setStyleSheet("""
            QScrollArea {
                border: none;
            }
        """)