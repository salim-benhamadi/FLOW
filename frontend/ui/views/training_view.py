from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                               QLabel, QPushButton, QComboBox, QProgressBar, 
                               QTableWidget, QTableWidgetItem, QFileDialog,
                               QMessageBox)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QFont
from ui.utils.EFFProcessor import EFFProcessor
from ui.widgets.EFFUploadDialog import EFFUploadDialog
from datetime import datetime
import asyncio
import traceback

import logging
from PySide6.QtCore import QThread, Signal

# Set up logging
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
            
            # Create a new event loop for this thread
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            
            # Run the task and get result
            result = self._loop.run_until_complete(self._safe_run_task())
            
            logger.debug("Task completed with result: %s", result)
            self.finished.emit(result)

        except Exception as e:
            logger.error("Error in worker: %s", str(e), exc_info=True)
            self.error.emit(str(e))
        finally:
            self._cleanup()

    async def _safe_run_task(self):
        """Wrapper to safely run the task with proper cleanup"""
        try:
            self._task = asyncio.create_task(self.run_task(**self.kwargs))
            return await self._task
        except asyncio.CancelledError:
            logger.debug("Task was cancelled")
            raise Exception("Operation cancelled")
        finally:
            if self._task and not self._task.done():
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass

    def _cleanup(self):
        """Clean up resources safely"""
        logger.debug("Starting worker cleanup")
        try:
            if self._loop and not self._loop.is_closed():
                # Cancel any pending tasks
                for task in asyncio.all_tasks(self._loop):
                    task.cancel()
                
                # Run the loop one last time to clean up
                try:
                    self._loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(self._loop)))
                except Exception:
                    pass
                
                self._loop.stop()
                self._loop.close()
        except Exception as e:
            logger.error("Error during cleanup: %s", str(e))
        finally:
            self._loop = None
            self._task = None
            self._is_running = False
            logger.debug("Worker cleanup completed")

    def stop(self):
        """Safely stop the worker"""
        logger.debug("Stopping worker")
        if self._is_running and self._loop and not self._loop.is_closed():
            try:
                # Schedule the cancellation in the worker's event loop
                self._loop.call_soon_threadsafe(self._cancel_task)
            except Exception as e:
                logger.error("Error cancelling task: %s", str(e))
        self.wait()
        logger.debug("Worker stopped")
    
    def _cancel_task(self):
        """Cancel the current task (called from the worker thread)"""
        if self._task and not self._task.done():
            self._task.cancel()
        
class RetrainingWorker(AsyncWorker):
    progress = Signal(int, str, str)  # progress value, event, status
    error = Signal(str)
    finished = Signal(object)

    async def run_task(self, file_path, product, lot, insertion):
        try:
            # Initialize EFF processor with the api_client
            processor = EFFProcessor(self.api_client)
            
            self.progress.emit(25, "Reading EFF file", "In Progress")
            
            # Process EFF file with additional information
            result = await processor.process_eff_file(
                file_path,
                product=product,
                lot=lot,
                insertion=insertion
            )
            
            self.progress.emit(75, f"Processing complete for {product} - {lot}", "In Progress")
            
            # Final verification
            if result.get('status') == 'success':
                self.progress.emit(100, "Processing complete", "Success")
                return True
            else:
                raise Exception(result.get('message', 'Unknown error occurred'))
                
        except Exception as e:
            logger.error("Error in RetrainingWorker: %s", str(e), exc_info=True)
            raise Exception(f"Error processing EFF file: {str(e)}")
        


class RetrainingTab(QWidget):
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
        self.workers = []
        self.current_worker = None
        self.filters = {
            'product': '',
            'lot': '',
            'test_name': '',
            'insertion': ''
        }
        self.initUI()
        QTimer.singleShot(0, self.load_initial_data)

    def load_initial_data(self):
        """Initialize data loading"""
        logger.debug("Starting initial data load")
        self.load_reference_data()
        #self.load_model_checkpoints()

    def create_worker(self, coro, *args, **kwargs):
        """Create and setup a worker thread"""
        worker = AsyncWorker(coro, *args, **kwargs)
        worker.finished.connect(lambda result: self.handle_worker_finished(worker, result))
        worker.error.connect(lambda error: self.handle_worker_error(worker, error))
        self.workers.append(worker)
        return worker

    def handle_worker_finished(self, worker, result):
        """Handle worker completion"""
        if worker in self.workers:
            self.workers.remove(worker)
        worker.deleteLater()

    def handle_worker_error(self, worker, error):
        """Handle worker error"""
        if worker in self.workers:
            self.workers.remove(worker)
        worker.deleteLater()
        self.show_error("Operation Failed", str(error))

    def load_reference_data(self):
        """Load reference data into table"""
        worker = self.create_worker(self._async_load_reference_data)
        worker.finished.connect(self._update_reference_table)
        worker.start()

    async def _async_load_reference_data(self):
        """Async operation to load reference data"""
        try:
            data = await self.api_client.get_reference_data_list()
            logger.debug(f"Loaded reference data: {len(data)} records")
            return data
        except Exception as e:
            logger.error(f"Error loading reference data: {str(e)}")
            raise

    def _update_reference_table(self, reference_data):
        """Update the reference table with data"""
        try:
            if not reference_data:
                logger.warning("No reference data received")
                return

            # Update filter options
            self._update_filter_options(reference_data)
            
            # Apply current filters to data
            filtered_data = self._filter_data(reference_data)
            
            self.referenceTable.setRowCount(0)
            for data in filtered_data:
                row_position = self.referenceTable.rowCount()
                self.referenceTable.insertRow(row_position)
                
                # Populate table cells
                self.referenceTable.setItem(row_position, 0, QTableWidgetItem(str(data.get('product', ''))))
                self.referenceTable.setItem(row_position, 1, QTableWidgetItem(str(data.get('lot', ''))))
                self.referenceTable.setItem(row_position, 2, QTableWidgetItem(str(data.get('insertion', ''))))
                self.referenceTable.setItem(row_position, 3, QTableWidgetItem(str(data.get('test_name', ''))))
                self.referenceTable.setItem(row_position, 4, QTableWidgetItem(str(data.get('test_number', ''))))
                self.referenceTable.setItem(row_position, 5, QTableWidgetItem(str(data.get('lsl', ''))))
                self.referenceTable.setItem(row_position, 6, QTableWidgetItem(str(data.get('usl', ''))))
                
                created_at = data.get('created_at', '')
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception as e:
                        logger.error(f"Error formatting date {created_at}: {str(e)}")
                        formatted_date = created_at
                    self.referenceTable.setItem(row_position, 7, QTableWidgetItem(formatted_date))

            logger.debug(f"Updated reference table with {self.referenceTable.rowCount()} rows")
        except Exception as e:
            logger.error(f"Error updating reference table: {str(e)}")
            self.show_error("Error updating reference table", str(e))

    def _update_filter_options(self, reference_data):
        """Update filter combo boxes with unique values"""
        products = sorted(set(str(data.get('product', '')) for data in reference_data))
        lots = sorted(set(str(data.get('lot', '')) for data in reference_data))
        test_names = sorted(set(str(data.get('test_name', '')) for data in reference_data))
        insertions = sorted(set(str(data.get('insertion', '')) for data in reference_data))

        current_product = self.productFilter.currentText()
        current_lot = self.lotFilter.currentText()
        current_test = self.testFilter.currentText()
        current_insertion = self.insertionFilter.currentText()

        self.productFilter.clear()
        self.lotFilter.clear()
        self.testFilter.clear()
        self.insertionFilter.clear()

        self.productFilter.addItem('')
        self.lotFilter.addItem('')
        self.testFilter.addItem('')
        self.insertionFilter.addItem('')

        self.productFilter.addItems(products)
        self.lotFilter.addItems(lots)
        self.testFilter.addItems(test_names)
        self.insertionFilter.addItems(insertions)

        # Restore previous selections if they still exist
        if current_product in products:
            self.productFilter.setCurrentText(current_product)
        if current_lot in lots:
            self.lotFilter.setCurrentText(current_lot)
        if current_test in test_names:
            self.testFilter.setCurrentText(current_test)
        if current_insertion in insertions:
            self.insertionFilter.setCurrentText(current_insertion)

    def _filter_data(self, reference_data):
        """Filter reference data based on current filter settings"""
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
        """Apply current filters and reload data"""
        self.load_reference_data()

    def clear_filters(self):
        """Clear all filters"""
        self.productFilter.setCurrentText('')
        self.lotFilter.setCurrentText('')
        self.testFilter.setCurrentText('')
        self.insertionFilter.setCurrentText('')
        self.load_reference_data()

    def load_model_checkpoints(self):
        """Load model checkpoints"""
        worker = self.create_worker(self._async_load_checkpoints)
        worker.finished.connect(self._update_checkpoints)
        worker.start()

    async def _async_load_checkpoints(self):
        """Async operation to load checkpoints"""
        #return await self.api_client.get_model_settings()
        pass

    def _update_checkpoints(self, settings):
        """Update checkpoint combo box"""
        try:
            if settings and 'checkpoints' in settings:
                self.checkpointCombo.clear()
                for checkpoint in settings['checkpoints']:
                    display_text = f"Model {checkpoint['version']}"
                    if checkpoint.get('is_latest'):
                        display_text += " (Latest)"
                    display_text += f" - {checkpoint['date']}"
                    self.checkpointCombo.addItem(display_text)
        except Exception as e:
            self.show_error("Error updating checkpoints", str(e))

    def add_reference_data(self):
        """Handle reference data file upload"""
        dialog = EFFUploadDialog(self)
        if dialog.exec_():
            upload_data = dialog.get_data()
            logger.debug("Upload data received: %s", upload_data)
            
            self.progressBar.show()
            self.progressBar.setValue(0)
            self.addDataBtn.setEnabled(False)
            
            # Clean up any existing worker
            self._cleanup_current_worker()
            
            # Create and start new worker
            try:
                self.current_worker = AsyncWorker(
                    run_task=self._async_process_reference_data,
                    **upload_data
                )
                self.current_worker.finished.connect(self._handle_upload_complete)
                self.current_worker.error.connect(self._handle_worker_error)
                self.current_worker.progress.connect(self._update_upload_progress)
                
                # Keep reference to worker
                self.current_worker.setParent(self)  # Set parent to prevent premature destruction
                self.current_worker.start()
                logger.debug("New worker started")
                
            except Exception as e:
                logger.error("Error creating worker: %s", str(e))
                self._handle_worker_error(str(e))
    def _handle_worker_error(self, error_msg):
        """Handle worker errors"""
        logger.error("Worker error: %s", error_msg)
        self.show_error("Processing Error", error_msg)
        self.addDataBtn.setEnabled(True)
        self.progressBar.hide()
        self._cleanup_current_worker()

    def _cleanup_current_worker(self):
        """Safely clean up the current worker"""
        if self.current_worker:
            logger.debug("Cleaning up current worker")
            try:
                self.current_worker.stop()
                self.current_worker.deleteLater()
            except Exception as e:
                logger.error("Error cleaning up worker: %s", str(e))
            finally:
                self.current_worker = None

    async def _async_process_reference_data(self, file_path, product, lot, insertion):
        """Async operation to process and upload reference data"""
        try:
            processor = EFFProcessor(self.api_client)
            result = await processor.process_eff_file(file_path, product, lot, insertion)
            await self.api_client.close() 
            return result
        except Exception as e:
            logger.error("Error processing data: %s", str(e), exc_info=True)
            await self.api_client.close() 
            raise

    def _update_upload_progress(self, value, event, status):
        """Update progress during upload"""
        self.progressBar.setValue(value)
        self.add_status_message(event, status)

    def _handle_upload_complete(self, result):
        """Handle completion of upload"""
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
        """Start model retraining"""
        self.retrainBtn.setEnabled(False)
        worker = self.create_worker(self._async_start_retraining)
        worker.progress.connect(self._update_training_progress)
        worker.finished.connect(lambda _: self._handle_training_complete())
        worker.start()

    async def _async_start_retraining(self):
        """Async operation to start retraining"""
        await self.api_client.start_model_retraining()
        return True

    def _update_training_progress(self, value, event, status):
        """Update progress during training"""
        self.progressBar.setValue(value)
        self.add_status_message(event, status)

    def _handle_training_complete(self):
        """Handle completion of training"""
        self.retrainBtn.setEnabled(True)
        self.progressBar.hide()
        self.add_status_message("Training completed", "Success")
        #self.load_model_checkpoints()

    def add_status_message(self, event: str, status: str):
        """Add message to status table"""
        current_time = datetime.now().strftime("%H:%M:%S")
        row_position = self.statusTable.rowCount()
        self.statusTable.insertRow(row_position)
        
        self.statusTable.setItem(row_position, 0, QTableWidgetItem(current_time))
        self.statusTable.setItem(row_position, 1, QTableWidgetItem(event))
        self.statusTable.setItem(row_position, 2, QTableWidgetItem(status))
        
        self.statusTable.scrollToBottom()

    def show_error(self, title: str, message: str):
        """Show error message box"""
        QMessageBox.critical(self, title, str(message))
        self.add_status_message(f"Error: {title}", "Failed")
        print(f"Error: {title}\n{message}")

    def closeEvent(self, event):
        """Handle widget close event"""
        logger.debug("Closing RetrainingTab")
        self._cleanup_current_worker()
        
        # Create a new event loop for cleanup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run cleanup in the new loop
            loop.run_until_complete(self.api_client.close())
        except Exception as e:
            logger.error("Error during cleanup: %s", str(e))
        finally:
            loop.close()
            event.accept()

    def initUI(self):
        layout = QVBoxLayout(self)

        # Model Checkpoints Section
        checkpointFrame = QFrame()
        checkpointFrame.setFrameStyle(QFrame.StyledPanel)
        checkpointLayout = QVBoxLayout(checkpointFrame)
        
        checkpointLabel = QLabel("Model Checkpoints")
        checkpointLabel.setFont(QFont("Arial", 12, QFont.Bold))
        
        self.checkpointCombo = QComboBox()
        
        checkpointLayout.addWidget(checkpointLabel)
        checkpointLayout.addWidget(self.checkpointCombo)
        layout.addWidget(checkpointFrame)

        # Control Panel
        controlPanel = QFrame()
        controlPanel.setFrameStyle(QFrame.StyledPanel)
        controlLayout = QHBoxLayout(controlPanel)

        # Add Data Button
        self.addDataBtn = QPushButton("Add Reference Data")
        self.addDataBtn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.addDataBtn.clicked.connect(self.add_reference_data)
        controlLayout.addWidget(self.addDataBtn)

        # Retrain Button
        self.retrainBtn = QPushButton("Start Retraining")
        self.retrainBtn.setStyleSheet("""
            QPushButton {
                background-color: #1849D6;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1438A8;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.retrainBtn.clicked.connect(self.start_retraining)
        controlLayout.addWidget(self.retrainBtn)

        # Schedule Section
        scheduleLayout = QVBoxLayout()
        scheduleLabel = QLabel("Automated Schedule:")
        scheduleLabel.setStyleSheet("font-weight: bold;")
        self.scheduleCombo = QComboBox()
        self.scheduleCombo.addItems(["Daily", "Weekly", "Monthly", "Custom"])
        self.scheduleCombo.setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 3px;
                min-width: 100px;
            }
        """)
        scheduleLayout.addWidget(scheduleLabel)
        scheduleLayout.addWidget(self.scheduleCombo)
        controlLayout.addLayout(scheduleLayout)

        layout.addWidget(controlPanel)

        # Progress Section
        progressFrame = QFrame()
        progressFrame.setFrameStyle(QFrame.StyledPanel)
        progressLayout = QVBoxLayout(progressFrame)

        self.progressLabel = QLabel("Processing Progress")
        self.progressLabel.setStyleSheet("font-weight: bold;")
        self.progressBar = QProgressBar()
        self.progressBar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 5px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #1849D6;
                border-radius: 5px;
            }
        """)
        self.progressBar.setValue(0)
        self.progressBar.hide()
        progressLayout.addWidget(self.progressLabel)
        progressLayout.addWidget(self.progressBar)

        layout.addWidget(progressFrame)

        # Add Filter Section
        filterFrame = QFrame()
        filterFrame.setFrameStyle(QFrame.StyledPanel)
        filterLayout = QHBoxLayout(filterFrame)

        # Product Filter
        productLabel = QLabel("Product:")
        self.productFilter = QComboBox()
        self.productFilter.setEditable(True)
        self.productFilter.currentTextChanged.connect(lambda: self.apply_filters())
        filterLayout.addWidget(productLabel)
        filterLayout.addWidget(self.productFilter)

        # Lot Filter
        lotLabel = QLabel("Lot:")
        self.lotFilter = QComboBox()
        self.lotFilter.setEditable(True)
        self.lotFilter.currentTextChanged.connect(lambda: self.apply_filters())
        filterLayout.addWidget(lotLabel)
        filterLayout.addWidget(self.lotFilter)

        # Test Name Filter
        testLabel = QLabel("Test Name:")
        self.testFilter = QComboBox()
        self.testFilter.setEditable(True)
        self.testFilter.currentTextChanged.connect(lambda: self.apply_filters())
        filterLayout.addWidget(testLabel)
        filterLayout.addWidget(self.testFilter)

        # Insertion Filter
        insertionLabel = QLabel("Insertion:")
        self.insertionFilter = QComboBox()
        self.insertionFilter.setEditable(True)
        self.insertionFilter.currentTextChanged.connect(lambda: self.apply_filters())
        filterLayout.addWidget(insertionLabel)
        filterLayout.addWidget(self.insertionFilter)

        # Clear Filters Button
        self.clearFiltersBtn = QPushButton("Clear Filters")
        self.clearFiltersBtn.clicked.connect(self.clear_filters)
        self.clearFiltersBtn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        filterLayout.addWidget(self.clearFiltersBtn)

        layout.addWidget(filterFrame)


        # Reference Data Table
        referenceFrame = QFrame()
        referenceFrame.setFrameStyle(QFrame.StyledPanel)
        referenceLayout = QVBoxLayout(referenceFrame)

        referenceLabel = QLabel("Reference Data")
        referenceLabel.setFont(QFont("Arial", 12, QFont.Bold))
        referenceLayout.addWidget(referenceLabel)

        self.referenceTable = QTableWidget()
        self.referenceTable.setColumnCount(8)
        self.referenceTable.setHorizontalHeaderLabels([
            "Product", "Lot", "Insertion", "Test Name", 
            "Test Number", "LSL", "USL", "Created At"
        ])
        self.referenceTable.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ccc;
                border-radius: 5px;
                gridline-color: #f0f0f0;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 6px;
                border: 1px solid #ddd;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
        self.referenceTable.horizontalHeader().setStretchLastSection(True)
        self.referenceTable.setSelectionBehavior(QTableWidget.SelectRows)
        self.referenceTable.setAlternatingRowColors(True)
        referenceLayout.addWidget(self.referenceTable)
        layout.addWidget(referenceFrame)

        # Status Table
        statusFrame = QFrame()
        statusFrame.setFrameStyle(QFrame.StyledPanel)
        statusLayout = QVBoxLayout(statusFrame)

        statusLabel = QLabel("Operation Status")
        statusLabel.setFont(QFont("Arial", 12, QFont.Bold))
        statusLayout.addWidget(statusLabel)

        self.statusTable = QTableWidget()
        self.statusTable.setColumnCount(3)
        self.statusTable.setHorizontalHeaderLabels(["Time", "Event", "Status"])
        self.statusTable.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ccc;
                border-radius: 5px;
                gridline-color: #f0f0f0;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 6px;
                border: 1px solid #ddd;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
        self.statusTable.horizontalHeader().setStretchLastSection(True)
        self.statusTable.setSelectionBehavior(QTableWidget.SelectRows)
        self.statusTable.setAlternatingRowColors(True)
        statusLayout.addWidget(self.statusTable)
        layout.addWidget(statusFrame)

        # Set overall layout margins and spacing
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)