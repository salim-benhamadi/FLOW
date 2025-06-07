from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
                               QFileDialog, QFrame, QScrollArea, QMessageBox, QGroupBox)
from PySide6.QtGui import QPixmap, QFont, QDragEnterEvent, QDropEvent
from PySide6.QtCore import Qt, Signal
from typing import List, Dict
import os
from ui.utils.EFFExtractor import EFFExtractor
from ui.utils.ExtractionWorker import ExtractionWorker

class ExtractionType:
    BACKEND = "BE"
    FRONTEND = "FE"

class UploadPage(QWidget):
    show_setting_signal = Signal()
    show_selection_signal = Signal(list)
    show_admin_login_signal = Signal()

    def __init__(self):
        super().__init__()
        self.uploaded_files = []
        self.progress_widgets = {}
        self.active_workers = []
        self.extractor = EFFExtractor()
        self.initUI()

    def initUI(self):
        self.setFixedWidth(480)
        self.setMinimumHeight(700)
        mainLayout = QVBoxLayout(self)
        self.setupHeaderSection(mainLayout)
        self.setupDragDropSection(mainLayout)
        self.setupSeparator(mainLayout)
        self.setupExtractionSection(mainLayout)
        self.setupFileListSection(mainLayout)
        mainLayout.setContentsMargins(40, 40, 40, 40)

    def setupHeaderSection(self, mainLayout):
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
                background-color: #5a6268;
            }
        """)
        self.adminButton.clicked.connect(self.show_admin_login)
        
        self.settingButton = QPushButton("Settings")
        self.settingButton.setStyleSheet("""
            QPushButton {
                background-color: #FFA500;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
                margin-left: 5px;
            }
        """)
        self.settingButton.clicked.connect(self.emit_show_setting)
        
        row1.addLayout(titleLayout)
        row1.addStretch()
        row1.addWidget(self.proceedButton, alignment=Qt.AlignRight)
        row1.addWidget(self.adminButton, alignment=Qt.AlignRight)
        row1.addWidget(self.settingButton, alignment=Qt.AlignRight)
        row1.setContentsMargins(0,0,0,20)
        mainLayout.addLayout(row1)

    def setupDragDropSection(self, mainLayout):
        self.dragDropSection = QLabel()
        self.dragDropSection.setStyleSheet("""
            border: 2px dashed #1849D6;
            background-color: white;
            border-radius: 5px;
        """)
        self.dragDropSection.setFixedHeight(150)
        self.dragDropSection.setAcceptDrops(True)
        
        dragDropLayout = QVBoxLayout(self.dragDropSection)
        
        uploadIcon = QLabel()
        iconPixmap = QPixmap('./src/frontend/resources/icons/upload.png')
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

    def setupExtractionSection(self, mainLayout):
        ebsTitle = QLabel('Upload from EBS')
        ebsTitle.setFont(QFont("Arial", 12, QFont.Bold))
        
        # Extract button
        self.extractButton = QPushButton('Extract')
        self.extractButton.setStyleSheet("""
            QPushButton {
                background-color: #1FBE42;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
                min-width: 40px;
            }
            QPushButton:disabled {
                background-color: grey;
            }
        """)
        self.extractButton.setEnabled(False)
        self.extractButton.clicked.connect(self.start_extraction)
        
        # Title row with extract button
        titleRow = QHBoxLayout()
        titleRow.addWidget(ebsTitle)
        titleRow.addStretch()
        titleRow.addWidget(self.extractButton)
        mainLayout.addLayout(titleRow)

        # BE Lot Input
        beLotLayout = QVBoxLayout()
        beLotLabel = QLabel('Backend lot number')
        self.beLotInput = QLineEdit()
        self.beLotInput.setPlaceholderText('Ex: ZA301387803')
        self.beLotInput.textChanged.connect(self.validate_inputs)
        self.beLotInput.setStyleSheet("""
            QLineEdit {
                border-radius: 5px;
                background-color: #F0F0F0;
                min-height: 30px;
                padding: 5px;
            }
        """)
        beLotLayout.addWidget(beLotLabel)
        beLotLayout.addWidget(self.beLotInput)

        # BE Insertion Input
        beInsertionLayout = QVBoxLayout()
        beInsertionLabel = QLabel('Backend insertion mode')
        self.beInsertionInput = QLineEdit()
        self.beInsertionInput.setPlaceholderText('B1,B2,B3')
        self.beInsertionInput.textChanged.connect(self.validate_inputs)
        self.beInsertionInput.setStyleSheet("""
            QLineEdit {
                border-radius: 5px;
                background-color: #F0F0F0;
                min-height: 30px;
                padding: 5px;
            }
        """)
        beInsertionLayout.addWidget(beInsertionLabel)
        beInsertionLayout.addWidget(self.beInsertionInput)

        # BE Input Row
        beInputRow = QHBoxLayout()
        beInputRow.addLayout(beLotLayout)
        beInputRow.addLayout(beInsertionLayout)
        mainLayout.addLayout(beInputRow)

        # FE Lot Input
        feLotLayout = QVBoxLayout()
        feLotLabel = QLabel('Frontend lot number')
        self.feLotInput = QLineEdit()
        self.feLotInput.setPlaceholderText('Ex: ZA301387803')
        self.feLotInput.textChanged.connect(self.validate_inputs)
        self.feLotInput.setStyleSheet("""
            QLineEdit {
                border-radius: 5px;
                background-color: #F0F0F0;
                min-height: 30px;
                padding: 5px;
            }
        """)
        feLotLayout.addWidget(feLotLabel)
        feLotLayout.addWidget(self.feLotInput)

        # FE Insertion Input
        feInsertionLayout = QVBoxLayout()
        feInsertionLabel = QLabel('Frontend insertion mode')
        self.feInsertionInput = QLineEdit()
        self.feInsertionInput.setPlaceholderText('S1,S2,S3')
        self.feInsertionInput.textChanged.connect(self.validate_inputs)
        self.feInsertionInput.setStyleSheet("""
            QLineEdit {
                border-radius: 5px;
                background-color: #F0F0F0;
                min-height: 30px;
                padding: 5px;
            }
        """)
        feInsertionLayout.addWidget(feInsertionLabel)
        feInsertionLayout.addWidget(self.feInsertionInput)

        # FE Input Row
        feInputRow = QHBoxLayout()
        feInputRow.addLayout(feLotLayout)
        feInputRow.addLayout(feInsertionLayout)
        mainLayout.addLayout(feInputRow)

        # Status area
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

    def closeEvent(self, event):
        """Handle cleanup when the widget is closed"""
        self.cleanup_workers()
        super().closeEvent(event)
    
    def cleanup_workers(self):
        """Clean up any running worker threads"""
        for worker in self.active_workers:
            if worker.isRunning():
                worker.stop()  # Signal the worker to stop
                worker.wait()  # Wait for it to finish
        self.active_workers.clear()

    def validate_inputs(self):
        """
        Validates that at least one set of inputs (BE or FE) is complete.
        Enables the extract button if either BE or FE inputs are valid.
        """
        be_valid = bool(self.beLotInput.text().strip() and self.beInsertionInput.text().strip())
        fe_valid = bool(self.feLotInput.text().strip() and self.feInsertionInput.text().strip())
        self.extractButton.setEnabled(be_valid or fe_valid)

    def parse_insertions(self, insertion_text: str) -> List[str]:
        return [x.strip() for x in insertion_text.split(',') if x.strip()]

    def validate_insertion_type(self, insertions: List[str], expected_prefix: str) -> bool:
        return all(insertion.startswith(expected_prefix) for insertion in insertions)

    def start_extraction(self):
        try:
            # Clean up any existing workers first
            self.cleanup_workers()
            
            extractions = {}
            
            # Process backend extraction if BE fields are filled
            be_lot = self.beLotInput.text().strip()
            be_insertions = self.parse_insertions(self.beInsertionInput.text())
            if be_lot and be_insertions:
                if not self.validate_insertion_type(be_insertions, 'B'):
                    QMessageBox.warning(self, "Input Error", "Backend insertions must start with 'B'")
                    return
                extractions[ExtractionType.BACKEND] = (be_lot, be_insertions)
            
            # Process frontend extraction if FE fields are filled
            fe_lot = self.feLotInput.text().strip()
            fe_insertions = self.parse_insertions(self.feInsertionInput.text())
            if fe_lot and fe_insertions:
                if not self.validate_insertion_type(fe_insertions, 'S'):
                    QMessageBox.warning(self, "Input Error", "Frontend insertions must start with 'S'")
                    return
                extractions[ExtractionType.FRONTEND] = (fe_lot, fe_insertions)
            
            if not extractions:
                QMessageBox.warning(self, "Input Error", "Please enter at least one valid extraction configuration")
                return

            self.statusArea.setText("Extracting files...")
            self.extractButton.setEnabled(False)
            
            # Start extraction workers for each configured type
            for extraction_type, (lot, insertions) in extractions.items():
                worker = ExtractionWorker(lot, insertions, self.extractor, extraction_type)
                worker.finished.connect(self.extraction_completed)
                worker.file_created.connect(self.add_extracted_file)
                # Important: Store worker reference to prevent premature garbage collection
                self.active_workers.append(worker)
                worker.start()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self.statusArea.setText("Extraction failed")
            self.extractButton.setEnabled(True)

    def extraction_completed(self, status_list: list):
        """Handle completion of extraction process"""
        for worker in self.active_workers[:]:  
            if not worker.isRunning():
                self.active_workers.remove(worker)
                worker.deleteLater() 

        if not self.active_workers:
            self.extractButton.setEnabled(True)
            success_count = sum(1 for status in status_list if status[0].strip() == "Finished!")
            total_count = len(status_list)
            
            result_message = f"Extraction completed successfully"
            self.statusArea.setText(result_message)
            
            if success_count < total_count:
                QMessageBox.warning(self, "Extraction Complete", result_message)
            else:
                QMessageBox.information(self, "Extraction Complete", result_message)

    def emit_show_setting(self):
        self.show_setting_signal.emit()
    
    def on_proceed_clicked(self):
        file_paths = [path for path, _ in self.uploaded_files]
        self.show_selection_signal.emit(file_paths)

    def show_admin_login(self):
        self.show_admin_login_signal.emit()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith(('.eff', '.tsf', '.zip')):
                self.addFile(file_path)
        self.proceedButton.setEnabled(True)

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
            self.proceedButton.setEnabled(True)
            for file in files:
                self.addFile(file)

    def addFile(self, filePath):
        if os.path.isfile(filePath):
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
            deleteButton.setIcon(QPixmap('./src/frontend/resources/icons/delete.png').scaled(
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
            return './src/frontend/resources/icons/ZIP.png'
        elif filePath.endswith('.eff'):
            return './src/frontend/resources/icons/EFF.png'
        elif filePath.endswith('.tsf'):
            return './src/frontend/resources/icons/TSF.png'
        return './src/frontend/resources/icons/default.png'

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

    def add_extracted_file(self, file_path: str):
        if os.path.isfile(file_path):
            self.addFile(file_path)
            self.proceedButton.setEnabled(True)