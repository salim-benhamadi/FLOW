from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QFrame)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, Signal
from ui.widgets.DonutProgress import DonutProgress
from ui.widgets.PhaseIndicator import PhaseIndicator, PhaseState
from ui.utils.DataProcessor import DataProcessor

class ProcessingPage(QWidget):
    show_results_signal = Signal(object)
    show_upload_signal = Signal()
    
    def __init__(self):
        super().__init__()
        self.selected_items = []
        self.files = []
        self.processed_data = None
        self.reference_config = {}  # Store reference configuration
        self.analysis_settings = {
            'sensitivity': 0.5,
            'model_version': 'v1'
        }
        self.processor = None
        self.initUI()

    def initUI(self):
        self.setFixedWidth(500)
        self.setMinimumHeight(500)
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                color: black;
            }
            QPushButton {
                border-radius: 5px;
                padding: 5px 15px;
                color: white;
            }
            QPushButton#cancelButton {
                background-color: #EF4444;
            }
            QPushButton#cancelButton:hover {
                background-color: #DC2626;
            }
            QFrame#phasesFrame {
                background-color: #F9FAFB;
                border-radius: 8px;
                padding: 10px;
            }
        """)

        mainLayout = QVBoxLayout(self)
        mainLayout.setSpacing(20)
        mainLayout.setContentsMargins(20, 20, 20, 20)

        headerLayout = QHBoxLayout()
        
        backButton = QPushButton("← Back")
        backButton.setFixedSize(80, 30)
        backButton.setStyleSheet("""
            QPushButton {
                background-color: #6B7280;
                color: white;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
        """)
        backButton.clicked.connect(self.show_upload_signal.emit)

        self.settingsLabel = QLabel("")
        self.settingsLabel.setFont(QFont("Arial", 9))
        self.settingsLabel.setStyleSheet("color: #6B7280;")
        
        headerLayout.addWidget(backButton)
        headerLayout.addStretch()
        headerLayout.addWidget(self.settingsLabel)
        
        mainLayout.addLayout(headerLayout)

        progressLayout = QVBoxLayout()
        progressLayout.setAlignment(Qt.AlignCenter)
        
        self.donutProgress = DonutProgress()
        self.donutProgress.setFixedSize(200, 200)
        progressLayout.addWidget(self.donutProgress, alignment=Qt.AlignCenter)
        
        self.statusLabel = QLabel("Initializing...")
        self.statusLabel.setAlignment(Qt.AlignCenter)
        self.statusLabel.setFont(QFont("Arial", 12))
        self.statusLabel.setStyleSheet("color: #374151; margin-top: 10px;")
        progressLayout.addWidget(self.statusLabel)
        
        mainLayout.addLayout(progressLayout)

        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.setObjectName("cancelButton")
        self.cancelButton.setFixedSize(120, 40)
        self.cancelButton.clicked.connect(self.cancel_processing)
        mainLayout.addWidget(self.cancelButton, alignment=Qt.AlignCenter)

        phasesFrame = QFrame()
        phasesFrame.setObjectName("phasesFrame")
        phasesLayout = QVBoxLayout(phasesFrame)
        
        phasesTitle = QLabel("Processing Phases")
        phasesTitle.setFont(QFont("Arial", 10, QFont.Bold))
        phasesLayout.addWidget(phasesTitle)
        
        self.phases = [
            PhaseIndicator("Loading Reference Data"),
            PhaseIndicator("Reading Input Files"),
            PhaseIndicator("Analyzing Distributions"),
            PhaseIndicator("Generating Results")
        ]
        
        for phase in self.phases:
            phasesLayout.addWidget(phase)
        
        mainLayout.addWidget(phasesFrame)
        mainLayout.addStretch()
        mainLayout.setContentsMargins(40,40,40,40)
        
        self.update_settings_display()
        
    def set_settings(self, settings: dict):
        """Store current settings for processing"""
        self.analysis_settings = settings
        self.update_settings_display()
        print(f"ProcessingPage: Settings updated to {settings}")
    
    def set_reference_config(self, reference_config: dict):
        """Store reference configuration for processing"""
        self.reference_config = reference_config
        print(f"ProcessingPage: Reference config set to {reference_config}")
        self.update_settings_display()
    
    def update_settings_display(self):
        """Update the settings display in the header"""
        sensitivity_pct = int(self.analysis_settings.get('sensitivity', 0.5) * 100)
        model_version = self.analysis_settings.get('model_version', 'v1')
        
        # Add reference source info
        ref_source = self.reference_config.get('source', 'unknown')
        if ref_source == 'cloud':
            ref_info = "Cloud"
        elif ref_source == 'local':
            ref_files_count = len(self.reference_config.get('files', []))
            ref_info = f"Local ({ref_files_count} files)" if ref_files_count > 0 else "Local"
        else:
            ref_info = "Default"
        
        settings_text = f"Sensitivity: {sensitivity_pct}% | Model: {model_version} | Ref: {ref_info}"
        self.settingsLabel.setText(settings_text)
        
    def update_progress(self, value):
        """Update progress bar and phase indicators"""
        self.donutProgress.setPercentage(value)
        self.statusLabel.setText(f"Processing... {value}%")
        
        # Reset all phases to pending first
        if value == 0:
            for phase in self.phases:
                phase.updateState(PhaseState.PENDING)
            self.phases[0].updateState(PhaseState.ACTIVE)
        
        # Update phases based on progress
        if value >= 20:
            self.phases[0].updateState(PhaseState.COMPLETED)
            if value < 50:
                self.phases[1].updateState(PhaseState.ACTIVE)
        if value >= 50:
            self.phases[1].updateState(PhaseState.COMPLETED)
            if value < 80:
                self.phases[2].updateState(PhaseState.ACTIVE)
        if value >= 80:
            self.phases[2].updateState(PhaseState.COMPLETED)
            if value < 100:
                self.phases[3].updateState(PhaseState.ACTIVE)
        if value >= 100:
            self.phases[3].updateState(PhaseState.COMPLETED)
            self.statusLabel.setText("Processing completed!")
            self.cancelButton.setText("Done")
            self.cancelButton.setStyleSheet("""
                QPushButton {
                    background-color: #22C55E;
                }
                QPushButton:hover {
                    background-color: #16A34A;
                }
            """)

    def set_data(self, selected_items: list, files: list):
        """Store selected items and files for processing"""
        self.selected_items = selected_items
        self.files = files
        print(f"ProcessingPage: Data set - {len(selected_items)} items, {len(files)} files")
        
        # Reset UI state
        self.donutProgress.setPercentage(0)
        self.statusLabel.setText("Initializing...")
        
        # Reset phases
        for phase in self.phases:
            phase.updateState(PhaseState.PENDING)
        
        # Don't auto-start processing here - wait for proper initialization

    def start_processing(self, total_files: int = None):
        """Start the processing with all configurations"""
        # Validate required data
        if not self.selected_items or not self.files:
            self.handle_error("Missing selected items or files")
            return
        
        # Set defaults if missing
        if not self.reference_config:
            self.reference_config = {
                "source": "local",
                "files": [],
                "cloud_selection": {}
            }
            print("Warning: No reference config found, using default")
        
        # Terminate any existing processor
        if self.processor and self.processor.isRunning():
            self.processor.terminate()
            self.processor.wait()
        
        # Create new DataProcessor with all configurations
        try:
            self.processor = DataProcessor(
                selected_items=self.selected_items,
                files=self.files,
                reference_config=self.reference_config,  # Pass reference configuration
                sensitivity=self.analysis_settings.get('sensitivity', 0.5),
                model_version=self.analysis_settings.get('model_version', 'v1')
            )
            
            # Connect signals
            self.processor.progress.connect(self.update_progress)
            self.processor.finished.connect(self.processing_finished)
            self.processor.result.connect(self.handle_result)
            self.processor.error.connect(self.handle_error)
            self.processor.file_processed.connect(self.on_file_processed)
            
            # Update UI state
            self.cancelButton.setText("Cancel")
            self.cancelButton.setStyleSheet("""
                QPushButton#cancelButton {
                    background-color: #EF4444;
                }
                QPushButton#cancelButton:hover {
                    background-color: #DC2626;
                }
            """)
            
            # Start first phase
            self.phases[0].updateState(PhaseState.ACTIVE)
            self.statusLabel.setText("Loading reference data...")
            
            # Start processing
            self.processor.start()
            print("DataProcessor started with full configuration")
            
        except Exception as e:
            self.handle_error(f"Failed to start processing: {str(e)}")

    def on_file_processed(self, file_path, success):
        """Handle individual file processing feedback"""
        if success:
            print(f"Successfully processed: {file_path}")
        else:
            print(f"Failed to process: {file_path}")

    def cancel_processing(self):
        """Cancel processing or return to upload page"""
        if self.processor and self.processor.isRunning():
            self.processor.terminate()
            self.processor.wait()
            self.processor = None
            self.statusLabel.setText("Processing cancelled")
            
            # Reset phases
            for phase in self.phases:
                phase.updateState(PhaseState.PENDING)
            
            self.show_upload_signal.emit()
        else:
            self.show_upload_signal.emit()

    def handle_result(self, result_data):
        """Handle processing results"""
        self.processed_data = result_data
        print(f"Processing completed successfully. Result shape: {result_data.shape if hasattr(result_data, 'shape') else 'Unknown'}")

    def handle_error(self, error_message):
        """Handle processing errors"""
        print(f"Processing error: {error_message}")
        self.statusLabel.setText(f"Error: {error_message}")
        
        # Mark current active phase as failed if any
        for phase in self.phases:
            if phase.state == PhaseState.ACTIVE:
                phase.updateState(PhaseState.PENDING)  # Reset to pending since no failed state
                break
        
        self.cancelButton.setText("Back")
        self.cancelButton.setStyleSheet("""
            QPushButton {
                background-color: #6B7280;
            }
            QPushButton:hover {
                background-color: #4B5563;
            }
        """)

    def processing_finished(self):
        """Handle processing completion"""
        self.statusLabel.setText("Processing completed!")
        self.cancelButton.setText("Done")
        self.cancelButton.setStyleSheet("""
            QPushButton {
                background-color: #22C55E;
            }
            QPushButton:hover {
                background-color: #16A34A;
            }
        """)
        
        if self.processed_data is not None:
            print("Emitting results signal")
            self.show_results_signal.emit(self.processed_data)
        else:
            print("Warning: No processed data available")
            self.handle_error("No data was generated during processing")