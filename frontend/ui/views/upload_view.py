from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
                               QFileDialog, QFrame, QScrollArea, QMessageBox, QGroupBox, QComboBox)
from PySide6.QtGui import QPixmap, QFont, QDragEnterEvent, QDropEvent, QIcon
from PySide6.QtCore import Qt, Signal
from typing import List, Dict
import os
import zipfile
import tempfile
import pickle
import datetime
from ui.utils.EFFExtractor import EFFExtractor, ExtractorType
from ui.utils.ExtractionWorker import ExtractionWorker
from ui.utils.EFFValidator import EFFValidator
from ui.utils.PathResources import resource_path

class LotInputWithInsertion(QWidget):
    deleted = Signal(object)
    
    def __init__(self, delete_icon_path, is_frontend=False):
        super().__init__()
        self.is_frontend = is_frontend
        self.delete_icon_path = delete_icon_path
        self.insertion_inputs = []
        self.initUI()
    
    def initUI(self):
        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(0, 5, 0, 5)
        
        firstRowLayout = QHBoxLayout()
        
        self.input = QLineEdit()
        self.input.setPlaceholderText('Lot Number')
        self.input.setStyleSheet("border-radius: 5px; background-color: #F0F0F0; min-height: 30px; padding: 5px;")
        firstRowLayout.addWidget(self.input)
        
        if self.is_frontend:
            self.wafer_input = QLineEdit()
            self.wafer_input.setPlaceholderText('Wafer')
            self.wafer_input.setStyleSheet("border-radius: 5px; background-color: #F0F0F0; min-height: 30px; padding: 5px;")
            firstRowLayout.addWidget(self.wafer_input)
        
        self.deleteBtn = QPushButton()
        self.deleteBtn.setFixedSize(30, 30)
        self.deleteBtn.setStyleSheet("QPushButton { border: none; } QPushButton:hover { background-color: #f0f0f0; }")
        self.deleteBtn.clicked.connect(lambda: self.deleted.emit(self))
        firstRowLayout.addWidget(self.deleteBtn)
        
        mainLayout.addLayout(firstRowLayout)
        
        insertionLabel = QLabel("Insertion Modes:")
        insertionLabel.setFont(QFont("Arial", 9))
        insertionLabel.setStyleSheet("margin-top: 5px; margin-bottom: 5px;")
        mainLayout.addWidget(insertionLabel)
        
        self.insertionLayout = QVBoxLayout()
        mainLayout.addLayout(self.insertionLayout)
        
        self.addInsertionBtn = QPushButton("Add Insertion")
        self.addInsertionBtn.setStyleSheet("QPushButton { color: #1849D6; border: none; text-align: left; }")
        self.addInsertionBtn.clicked.connect(self.add_insertion)
        mainLayout.addWidget(self.addInsertionBtn)
        
        self.add_insertion()
    
    def add_insertion(self):
        insertionWidget = QWidget()
        insertionLayout = QHBoxLayout(insertionWidget)
        insertionLayout.setContentsMargins(0, 0, 0, 0)
        insertionLayout.setSpacing(5)
        
        insertionInput = QLineEdit()
        insertionInput.setPlaceholderText(f'Insertion {len(self.insertion_inputs) + 1}')
        insertionInput.setStyleSheet("border-radius: 5px; background-color: #F0F0F0; min-height: 25px; padding: 3px;")
        
        removeBtn = QPushButton("Remove")
        removeBtn.setFixedSize(60, 25)
        removeBtn.setStyleSheet("QPushButton { background-color: #FF4444; color: white; border-radius: 3px; }")
        removeBtn.clicked.connect(lambda: self.remove_insertion(insertionWidget, insertionInput))
        
        insertionLayout.addWidget(insertionInput)
        insertionLayout.addWidget(removeBtn)
        
        self.insertionLayout.addWidget(insertionWidget)
        self.insertion_inputs.append(insertionInput)
        
        self.update_remove_buttons()
    
    def remove_insertion(self, widget, input_field):
        if len(self.insertion_inputs) > 1:
            self.insertion_inputs.remove(input_field)
            widget.deleteLater()
            self.update_remove_buttons()
    
    def update_remove_buttons(self):
        for i, widget in enumerate(self.insertionLayout.parentWidget().findChildren(QWidget)):
            if hasattr(widget, 'layout') and widget.layout():
                remove_btn = None
                for j in range(widget.layout().count()):
                    item = widget.layout().itemAt(j)
                    if item and isinstance(item.widget(), QPushButton) and item.widget().text() == "Remove":
                        remove_btn = item.widget()
                        break
                if remove_btn:
                    remove_btn.setVisible(len(self.insertion_inputs) > 1)
    
    def get_insertions(self):
        return [inp.text().strip() for inp in self.insertion_inputs if inp.text().strip()]

class UploadPage(QWidget):
    show_selection_signal = Signal(list) 
    show_admin_login_signal = Signal()
    show_settings_signal = Signal()
    load_dashboard_signal = Signal(object)

    def __init__(self):
        super().__init__()
        self.uploaded_files = []
        self.progress_widgets = {}
        self.active_workers = []
        self.current_extraction_index = 0
        self.chips_to_process = []
        self.lot_inputs = []
        self.extracted_files = []
        
        self.upload_dir = os.path.dirname(os.path.dirname(__file__))
        self.output_dir = resource_path(os.path.join('./resources/output'))
        self.temp_dir = tempfile.mkdtemp()
        self.add_icon = resource_path(os.path.join('./resources/icons', 'add.png'))
        self.delete_icon = resource_path(os.path.join('./resources/icons', 'delete.png'))
        self.substruct_icon = resource_path(os.path.join('./resources/icons', 'substruct.png'))
        
        self.extractors = {
            'backend': EFFExtractor(ExtractorType.BACKEND),
            'frontend': EFFExtractor(ExtractorType.FRONTEND)
        }
        
        self.initUI()

    def initUI(self):
        self.setFixedWidth(530)
        self.setMinimumHeight(700)
        self.setAcceptDrops(True)
        
        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        
        self.setupHeaderSection(mainLayout)
        
        scrollArea = QScrollArea()
        scrollArea.setWidgetResizable(True)
        scrollArea.setStyleSheet("QScrollArea { border: none; }")
        
        scrollContent = QWidget()
        scrollLayout = QVBoxLayout(scrollContent)
        scrollLayout.setContentsMargins(40, 20, 40, 40)
        
        self.setupDashboardImportSection(scrollLayout)
        self.setupDragDropSection(scrollLayout)
        self.setupSeparator(scrollLayout)
        self.setupLotBasedSection(scrollLayout)
        self.setupFileListSection(scrollLayout)
        
        scrollArea.setWidget(scrollContent)
        mainLayout.addWidget(scrollArea)

    def setupHeaderSection(self, mainLayout):
        headerWidget = QWidget()
        headerWidget.setFixedHeight(80)
        headerLayout = QVBoxLayout(headerWidget)
        headerLayout.setContentsMargins(40, 20, 40, 0)
        
        row1 = QHBoxLayout()
        titleLayout = QVBoxLayout()
        
        title = QLabel("Media upload")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setStyleSheet("margin-bottom: 0px;")
        subtitle = QLabel("Add your documents here....")
        subtitle.setFont(QFont("Arial", 8))
        subtitle.setStyleSheet("color: gray; margin-top: 0px; margin-bottom: 20px;")
        
        titleLayout.addWidget(title)
        titleLayout.addWidget(subtitle)
        
        self.settingsButton = QPushButton("Settings")
        try:
            settings_icon = resource_path(os.path.join('./resources/icons', 'settings.png'))
            if os.path.exists(settings_icon):
                self.settingsButton.setIcon(QIcon(settings_icon))
        except:
            pass
        
        self.settingsButton.setStyleSheet("""
            QPushButton {
                background-color: #6C757D;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
                margin-right: 5px;
            }
            QPushButton:hover {
                background-color: #5A6268;
            }
        """)
        self.settingsButton.clicked.connect(self.show_settings)
        
        self.proceedButton = QPushButton("Proceed")
        self.proceedButton.setStyleSheet("""
            QPushButton {
                background-color: #1849D6;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
            }
            QPushButton:disabled {
                background-color: grey;
            }
        """)
        self.proceedButton.setEnabled(False)
        self.proceedButton.clicked.connect(self.on_proceed_clicked)
        
        self.adminButton = QPushButton("Admin")
        self.adminButton.setStyleSheet("""
            QPushButton {
                background-color: #FF0000;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
                margin-left: 5px;
            }
            QPushButton:hover {
                background-color: #CC0000;
            }
        """)
        self.adminButton.clicked.connect(self.show_admin_login)
        
        row1.addLayout(titleLayout)
        row1.addStretch()
        row1.addWidget(self.settingsButton, alignment=Qt.AlignRight)
        row1.addWidget(self.proceedButton, alignment=Qt.AlignRight)
        row1.addWidget(self.adminButton, alignment=Qt.AlignRight)
        row1.setContentsMargins(0,0,0,20)
        headerLayout.addLayout(row1)
        
        mainLayout.addWidget(headerWidget)
    
    def show_settings(self):
        """Emit signal to show settings page"""
        self.show_settings_signal.emit()

    def setupDashboardImportSection(self, mainLayout):
        """Setup import dashboard section"""
        importSection = QWidget()
        importSection.setStyleSheet("""
            border: 2px solid #17A2B8;
            background-color: #F8F9FA;
            border-radius: 5px;
            padding: 10px;
        """)
        importSection.setFixedHeight(80)
        
        importLayout = QHBoxLayout(importSection)
        
        importIcon = QLabel()
        importIcon.setText("📊")
        importIcon.setFont(QFont("Arial", 20))
        
        importIcon.setStyleSheet("border: none; padding: 5px;")
        importIcon.setAlignment(Qt.AlignCenter)
        
        importTextLayout = QVBoxLayout()
        importText = QLabel('Import Dashboard')
        importText.setFont(QFont("Arial", 10, QFont.Bold))
        importText.setStyleSheet("border: none; color: #17A2B8;")
        
        importSubtext = QLabel('Load a previously exported dashboard')
        importSubtext.setFont(QFont("Arial", 8))
        importSubtext.setStyleSheet("border: none; color: gray;")
        
        importTextLayout.addWidget(importText)
        importTextLayout.addWidget(importSubtext)
        importTextLayout.setSpacing(0)
        self.importDashboardButton = QPushButton("Import Dashboard")
        self.importDashboardButton.setStyleSheet("""
            QPushButton {
                background-color: #17A2B8;
                color: white;
                border-radius: 5px;
                padding: 8px 15px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        self.importDashboardButton.clicked.connect(self.importDashboard)
        
        importLayout.addWidget(importIcon)
        importLayout.addLayout(importTextLayout)
        importLayout.addStretch()
        importLayout.addWidget(self.importDashboardButton)
        
        mainLayout.addWidget(importSection)
        
        importMessage = QLabel("Import a .pkl dashboard file to restore a previous session")
        importMessage.setStyleSheet("color: gray; margin-top: 5px; margin-bottom: 20px; font-size: 10px;")
        mainLayout.addWidget(importMessage)

    def importDashboard(self):
        """Import dashboard from pickle file"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Dashboard",
            "",
            "Dashboard Files (*.pkl)"
        )
        if path:
            try:
                with open(path, 'rb') as f:
                    dashboard_data = pickle.load(f)
                
                # Validate dashboard data structure
                if not isinstance(dashboard_data, dict):
                    raise ValueError("Invalid dashboard file format")
                
                required_keys = ['data', 'visible_columns', 'all_columns', 'table_data', 'metadata']
                if not all(key in dashboard_data for key in required_keys):
                    raise ValueError("Dashboard file is missing required data")
                
                # Show confirmation dialog
                metadata = dashboard_data.get('metadata', {})
                export_date = metadata.get('export_date', 'Unknown')
                rows = metadata.get('rows', 0)
                columns = metadata.get('columns', 0)
                
                reply = QMessageBox.question(
                    self,
                    "Import Dashboard",
                    f"Dashboard Information:\n"
                    f"Export Date: {export_date}\n"
                    f"Rows: {rows}\n"
                    f"Columns: {columns}\n\n"
                    f"Do you want to import this dashboard?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    # Emit signal to load dashboard
                    self.load_dashboard_signal.emit(dashboard_data)
                    
                    QMessageBox.information(
                        self,
                        "Import Successful",
                        "Dashboard imported successfully!"
                    )
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Import Failed",
                    f"Failed to import dashboard:\n{str(e)}"
                )

    def setupDragDropSection(self, mainLayout):
        self.dragDropSection = QWidget()
        self.dragDropSection.setStyleSheet("""
            border: 2px dashed #1849D6;
            background-color: white;
            border-radius: 5px;
        """)
        self.dragDropSection.setFixedHeight(150)
        self.dragDropSection.setAcceptDrops(True)
        
        dragDropLayout = QVBoxLayout(self.dragDropSection)
        
        uploadIcon = QLabel()
        iconPixmap = QPixmap(resource_path('./resources/icons/upload.png'))
        iconPixmap = iconPixmap.scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        uploadIcon.setPixmap(iconPixmap)
        uploadIcon.setStyleSheet("border : none")
        uploadIcon.setAlignment(Qt.AlignCenter)
        
        uploadText = QLabel('Drag your file(s) or <span style="color:#1849D6;">browse</span>')
        uploadText.setStyleSheet("border : none;")
        uploadText.setAlignment(Qt.AlignCenter)
        
        dragDropLayout.addStretch()
        dragDropLayout.addWidget(uploadIcon, alignment=Qt.AlignCenter)
        dragDropLayout.addWidget(uploadText, alignment=Qt.AlignCenter)
        dragDropLayout.addStretch()
        
        mainLayout.addWidget(self.dragDropSection)
        message = QLabel("Only support .eff, .tsf, and .zip files")
        message.setStyleSheet("color: gray; margin-top: 0px; margin-bottom: 30px;")
        mainLayout.addWidget(message)
        
        self.dragDropSection.mousePressEvent = self.openFileDialog

    def setupSeparator(self, mainLayout):
        self.div1 = QFrame()
        self.div1.setFrameShape(QFrame.HLine)
        self.div1.setFrameShadow(QFrame.Sunken)
        self.div1.setFixedWidth(165)
        
        self.div2 = QFrame()
        self.div2.setFrameShape(QFrame.HLine)
        self.div2.setFrameShadow(QFrame.Sunken)
        self.div2.setFixedWidth(165)
        
        sepearatorLayout = QHBoxLayout()
        separator = QLabel('or')
        separator.setStyleSheet("color: gray; margin : 0px; text-align: center;")
        separator.setFixedWidth(20)
        sepearatorLayout.addWidget(self.div1)
        sepearatorLayout.addWidget(separator)
        sepearatorLayout.addWidget(self.div2)
        
        mainLayout.addLayout(sepearatorLayout)

    def setupLotBasedSection(self, mainLayout):
        lotNumbersSection = QVBoxLayout()
        lotHeaderLayout = QHBoxLayout()
        lotLabel = QLabel("Lot Numbers")
        lotLabel.setFont(QFont("Arial", 10, QFont.Bold))
        
        self.addBackendLotButton = QPushButton("Add Backend Lot")
        self.addBackendLotButton.setIcon(QIcon(self.add_icon))
        self.addBackendLotButton.setFixedSize(120, 30)
        self.addBackendLotButton.setStyleSheet("""
            QPushButton { 
                border: none;
                color: #1849D6;
                text-align: left;
                padding-left: 5px;
            }
        """)
        self.addBackendLotButton.clicked.connect(lambda: self.add_lot_field(False))

        self.addFrontendLotButton = QPushButton("Add Frontend Lot")
        self.addFrontendLotButton.setIcon(QIcon(self.add_icon))
        self.addFrontendLotButton.setFixedSize(120, 30)
        self.addFrontendLotButton.setStyleSheet("""
            QPushButton { 
                border: none;
                color: #1849D6;
                text-align: left;
                padding-left: 5px;
            }
        """)
        self.addFrontendLotButton.clicked.connect(lambda: self.add_lot_field(True))

        lotHeaderLayout.addWidget(lotLabel)
        lotHeaderLayout.addStretch()
        lotHeaderLayout.addWidget(self.addBackendLotButton)
        lotHeaderLayout.addWidget(self.addFrontendLotButton)
        lotNumbersSection.addLayout(lotHeaderLayout)
        
        self.lotFieldsLayout = QVBoxLayout()
        lotNumbersSection.addLayout(self.lotFieldsLayout)
        mainLayout.addLayout(lotNumbersSection)

        self.extractButton = QPushButton('Extract')
        self.extractButton.setStyleSheet("""
            QPushButton {
                background-color: #1FBE42;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
                min-width: 40px;
                margin-top: 20px;
            }
            QPushButton:disabled {
                background-color: grey;
            }
        """)
        self.extractButton.setEnabled(False)
        self.extractButton.clicked.connect(self.start_extraction)
        mainLayout.addWidget(self.extractButton)

        self.statusArea = QLabel("Ready to extract files...")
        self.statusArea.setStyleSheet("color: gray; margin-top: 5px; margin-bottom: 10px;")
        mainLayout.addWidget(self.statusArea)

    def setupFileListSection(self, mainLayout):
        self.clearFilesButton = QPushButton("Clear All")
        self.clearFilesButton.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #FF0000;
                border: 1px solid #FF0000;
                border-radius: 5px;
                padding: 5px 15px;
            }
        """)
        self.clearFilesButton.clicked.connect(self.clearAllFiles)
        mainLayout.addWidget(self.clearFilesButton)
        
        self.fileListScrollArea = QScrollArea()
        self.fileListScrollArea.setMinimumHeight(200)
        self.fileListScrollArea.setWidgetResizable(True)
        self.fileListScrollArea.setStyleSheet("QScrollArea { border: none; }")
        
        self.fileListContent = QWidget()
        self.fileListLayout = QVBoxLayout(self.fileListContent)
        self.fileListLayout.setAlignment(Qt.AlignTop)
        self.fileListScrollArea.setWidget(self.fileListContent)
        
        mainLayout.addWidget(self.fileListScrollArea)
        mainLayout.addStretch()

    def extract_zip_file(self, zip_path):
        try:
            extracted_files = []
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file_info in zip_ref.infolist():
                    if file_info.filename.endswith(('.eff', '.tsf')):
                        extract_path = os.path.join(self.temp_dir, os.path.basename(file_info.filename))
                        with zip_ref.open(file_info) as source, open(extract_path, 'wb') as target:
                            target.write(source.read())
                        extracted_files.append(extract_path)
            return extracted_files
        except Exception as e:
            QMessageBox.warning(self, "Extraction Error", f"Failed to extract {zip_path}: {str(e)}")
            return []

    def add_lot_field(self, is_frontend=False):
        lot_input = LotInputWithInsertion(self.delete_icon, is_frontend)
        lot_input.deleted.connect(self.remove_lot_field)
        lot_input.input.textChanged.connect(self.validate_inputs)
        if is_frontend:
            lot_input.wafer_input.textChanged.connect(self.validate_inputs)
        for insertion_input in lot_input.insertion_inputs:
            insertion_input.textChanged.connect(self.validate_inputs)
        self.lot_inputs.append(lot_input)
        self.lotFieldsLayout.addWidget(lot_input)
        self.update_delete_buttons()

    def remove_lot_field(self, lot_widget):
        if len(self.lot_inputs) > 0:
            self.lot_inputs.remove(lot_widget)
            lot_widget.deleteLater()
            self.update_delete_buttons()
            self.validate_inputs()

    def update_delete_buttons(self):
        for i, lot_input in enumerate(self.lot_inputs):
            lot_input.deleteBtn.setVisible(len(self.lot_inputs) > 0)

    def validate_inputs(self):
        lots_valid = True
        has_insertions = False
        
        for lot_input in self.lot_inputs:
            if lot_input.is_frontend:
                if not (lot_input.input.text().strip() and lot_input.wafer_input.text().strip()):
                    lots_valid = False
                    break
            else:
                if not lot_input.input.text().strip():
                    lots_valid = False
                    break
            
            insertions = lot_input.get_insertions()
            if insertions:
                has_insertions = True
        
        self.extractButton.setEnabled(lots_valid and has_insertions and len(self.lot_inputs) > 0)
        
        if lots_valid and has_insertions:
            self.check_existing_files()

    def get_expected_filename(self, lot, insertion, wafer=None):
        if wafer:
            return f"{lot}_{wafer}_{insertion}.eff"
        return f"{lot}_{insertion}.eff"

    def check_file_exists(self, lot, insertion, wafer=None):
        expected_file = os.path.join(self.output_dir, self.get_expected_filename(lot, insertion, wafer))
        return os.path.exists(expected_file)

    def add_file_if_not_exists(self, file_path):
        existing_paths = [path for path, _ in self.uploaded_files]
        if file_path not in existing_paths and os.path.exists(file_path):
            self.addFile(file_path)
            self.proceedButton.setEnabled(True)

    def check_existing_files(self):
        for lot_input in self.lot_inputs:
            lot = lot_input.input.text().strip()
            if not lot:
                continue
                
            wafer = lot_input.wafer_input.text().strip() if lot_input.is_frontend else None
            insertions = lot_input.get_insertions()
            
            for insertion in insertions:
                if insertion and self.check_file_exists(lot, insertion, wafer):
                    file_path = os.path.join(self.output_dir, self.get_expected_filename(lot, insertion, wafer))
                    self.add_file_if_not_exists(file_path)

    def start_extraction(self):
        try:
            self.chips_to_process = []
            for lot_input in self.lot_inputs:
                lot = lot_input.input.text().strip()
                if not lot:
                    continue

                if lot_input.is_frontend:
                    wafer = lot_input.wafer_input.text().strip()
                    if not wafer:
                        continue
                else:
                    wafer = None

                insertions = lot_input.get_insertions()

                for insertion in insertions:
                    if not self.check_file_exists(lot, insertion, wafer):
                        self.chips_to_process.append((lot, insertion, wafer, lot_input.is_frontend))
                    else:
                        file_path = os.path.join(self.output_dir, self.get_expected_filename(lot, insertion, wafer))
                        self.add_file_if_not_exists(file_path)

            if not self.chips_to_process:
                QMessageBox.information(self, "Information", "All files have already been extracted!")
                return

            self.current_extraction_index = 0
            self.statusArea.setText("Starting extraction...")
            self.extractButton.setEnabled(False)
            self.process_next_chip()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.statusArea.setText("Extraction failed")
            self.extractButton.setEnabled(True)

    def process_next_chip(self):
        if self.current_extraction_index < len(self.chips_to_process):
            current_lot, current_insertion, current_wafer, is_frontend = self.chips_to_process[self.current_extraction_index]
            
            extractor = self.extractors['frontend'] if is_frontend else self.extractors['backend']
            
            self.extraction_worker = ExtractionWorker(
                current_lot,
                [current_insertion],
                extractor,
                wafer=current_wafer,
                max_workers=os.cpu_count()
            )
            
            self.extraction_worker.finished.connect(self.extraction_completed)
            self.extraction_worker.file_created.connect(
                lambda f: self.add_extracted_file(f, current_lot, current_insertion, current_wafer)
            )
            self.extraction_worker.progress.connect(self.update_progress)
            self.extraction_worker.start()

            status_text = f"Processing lot {current_lot}"
            if current_wafer:
                status_text += f", wafer {current_wafer}"
            status_text += f", insertion {current_insertion}..."
            self.statusArea.setText(status_text)
        else:
            self.extractButton.setEnabled(True)
            self.statusArea.setText("Extraction completed for all chips")

    def extraction_completed(self, status_list):
        current_lot, current_insertion, current_wafer, _ = self.chips_to_process[self.current_extraction_index]
        success = any(status[0].strip() == "Finished!" for status in status_list)
        
        if success:
            output_file = os.path.join(self.output_dir, 
                                     self.get_expected_filename(current_lot, current_insertion, current_wafer))
            try:
                self.add_extracted_file(output_file, current_lot, current_insertion, current_wafer)
            except Exception as e:
                QMessageBox.warning(self, "Processing Warning", f"Error processing file: {str(e)}")
        
        self.current_extraction_index += 1
        if self.current_extraction_index < len(self.chips_to_process):
            self.process_next_chip()
        else:
            self.extractButton.setEnabled(True)
            self.statusArea.setText("All extractions completed")
            QMessageBox.information(self, "Extraction Complete", "All chips have been processed")

    def update_progress(self, filename, progress, real_filename, filesize):
        if self.current_extraction_index < len(self.chips_to_process):
            current_lot, current_insertion, current_wafer, _ = self.chips_to_process[self.current_extraction_index]
            status_text = f"Processing lot {current_lot}"
            if current_wafer:
                status_text += f", wafer {current_wafer}"
            status_text += f", insertion {current_insertion}: {progress}%"
            self.statusArea.setText(status_text)

    def add_extracted_file(self, file_path, lot, insertion, wafer=None):
        if os.path.isfile(file_path):
            new_filename = self.get_expected_filename(lot, insertion, wafer)
            new_path = os.path.join(self.output_dir, new_filename)
            
            if any(new_path == path for path, _ in self.uploaded_files):
                return
                
            if file_path != new_path:
                try:
                    os.rename(file_path, new_path)
                    self.addFile(new_path)
                except Exception as e:
                    QMessageBox.warning(self, "File Error", f"Error renaming file: {str(e)}")
                    if not any(file_path == path for path, _ in self.uploaded_files):
                        self.addFile(file_path)
            else:
                if not any(file_path == path for path, _ in self.uploaded_files):
                    self.addFile(file_path)
            
            self.proceedButton.setEnabled(True)

    def closeEvent(self, event):
        self.cleanup_workers()
        super().closeEvent(event)
    
    def cleanup_workers(self):
        for worker in self.active_workers:
            if worker.isRunning():
                worker.stop()
                worker.wait()
        self.active_workers.clear()
    
    def on_proceed_clicked(self):
        all_files = []
        for file_path, _ in self.uploaded_files:
            if file_path.endswith('.zip'):
                extracted = self.extract_zip_file(file_path)
                all_files.extend(extracted)
            else:
                all_files.append(file_path)
        
        self.show_selection_signal.emit(all_files)

    def show_admin_login(self):
        self.show_admin_login_signal.emit()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                file_path = url.toLocalFile()
                if file_path.endswith(('.eff', '.tsf', '.zip')):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        files_added = False
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith(('.eff', '.tsf', '.zip')):
                existing_paths = [path for path, _ in self.uploaded_files]
                if file_path not in existing_paths:
                    self.addFile(file_path)
                    files_added = True
        
        if files_added:
            self.proceedButton.setEnabled(True)
        event.acceptProposedAction()

    def openFileDialog(self, event):
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files",
            "",
            "EFF Files (*.eff);;TSF Files (*.tsf);;ZIP Files (*.zip)",
            options=options
        )
        if files:
            files_added = False
            for file in files:
                existing_paths = [path for path, _ in self.uploaded_files]
                if file not in existing_paths:
                    self.addFile(file)
                    files_added = True
            
            if files_added:
                self.proceedButton.setEnabled(True)

    def addFile(self, filePath):
        if os.path.isfile(filePath):
            existing_paths = [path for path, _ in self.uploaded_files]
            if filePath in existing_paths:
                return
                
            fileName = os.path.basename(filePath)
            fileSize = os.path.getsize(filePath) / 1024.0
            fileLayout = QHBoxLayout()
            fileWidget = QWidget()
            fileWidget.setStyleSheet("""
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                max-height: 60px
            """)
            fileWidget.setLayout(fileLayout)
            
            fileIcon = QLabel()
            iconPath = self.get_icon_path(filePath)
            iconSize = 40
            fileIcon.setPixmap(QPixmap(iconPath).scaled(
                iconSize,
                iconSize,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
            fileIcon.setStyleSheet("border: none;")

            fileTitleLayout = QVBoxLayout()
            fileTitle = QLabel(fileName)
            fileTitle.setStyleSheet("color: black; border: none;")
            fileSizeLabel = QLabel(f"{fileSize:.2f} KB")
            fileSizeLabel.setStyleSheet("color: gray; font-size: 10px; border: none;")
            
            fileTitleLayout.addWidget(fileTitle)
            fileTitleLayout.addWidget(fileSizeLabel)
            
            deleteButton = QPushButton()
            deleteButton.setIcon(QPixmap(resource_path('./resources/icons/delete.png')).scaled(
                20,
                20,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            ))
            deleteButton.setStyleSheet("border: none;")
            deleteButton.clicked.connect(lambda: self.removeFile(filePath, fileWidget))
            
            fileLayout.addWidget(fileIcon)
            fileLayout.addLayout(fileTitleLayout)
            fileLayout.addStretch()
            fileLayout.addWidget(deleteButton)
            self.fileListLayout.addWidget(fileWidget)
            self.uploaded_files.append((filePath, fileWidget))

    def get_icon_path(self, filePath):
        if filePath.endswith('.zip'):
            return resource_path('./resources/icons/ZIP.png')
        elif filePath.endswith('.eff'):
            return resource_path('./resources/icons/EFF.png')
        elif filePath.endswith('.tsf'):
            return resource_path('./resources/icons/TSF.png')
        return resource_path('./resources/icons/default.png')

    def removeFile(self, filePath, fileWidget):
        for path, widget in self.uploaded_files:
            if path == filePath:
                self.uploaded_files.remove((path, widget))
                widget.setParent(None)
                widget.deleteLater()
                break
        if not self.uploaded_files:
            self.proceedButton.setEnabled(False)

    def clearAllFiles(self):
        while self.uploaded_files:
            filePath, fileWidget = self.uploaded_files.pop()
            fileWidget.setParent(None)
            fileWidget.deleteLater()
        self.proceedButton.setEnabled(False)
        self.deleteBtn.set