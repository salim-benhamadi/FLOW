# File : processing.py
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
        self.initUI()

    def initUI(self):
        self.setFixedWidth(480)
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
                background-color: #EF4444;  /* red-500 */
            }
            QPushButton#cancelButton:hover {
                background-color: #DC2626;  /* red-600 */
            }
            QFrame#phasesFrame {
                background-color: #F9FAFB;  /* gray-50 */
                border-radius: 8px;
                padding: 10px;
            }
        """)

        # Create main layout
        mainLayout = QVBoxLayout(self)
        mainLayout.setSpacing(20)
        mainLayout.setContentsMargins(20, 20, 20, 20)

        # Header
        headerLayout = QHBoxLayout()
        
        # Title and subtitle
        titleLayout = QVBoxLayout()
        self.title = QLabel("Processing")
        self.title.setFont(QFont("Arial", 12, QFont.Bold))
        self.subtitle = QLabel("Your files are being processed")
        self.subtitle.setFont(QFont("Arial", 8))
        self.subtitle.setStyleSheet("color: #6B7280;")  
        
        titleLayout.addWidget(self.title)
        titleLayout.addWidget(self.subtitle)
        
        # Cancel button
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.setObjectName("cancelButton")
        self.cancelButton.clicked.connect(self.cancel_processing)
        
        headerLayout.addLayout(titleLayout)
        headerLayout.addStretch()
        headerLayout.addWidget(self.cancelButton)
        
        mainLayout.addLayout(headerLayout)

        # Donut Progress
        self.donutProgress = DonutProgress(self)
        
        # Center the donut progress
        progressLayout = QHBoxLayout()
        progressLayout.addStretch()
        progressLayout.addWidget(self.donutProgress)
        progressLayout.addStretch()
        mainLayout.addLayout(progressLayout)
        
        # Status label
        self.statusLabel = QLabel("Initializing...")
        self.statusLabel.setAlignment(Qt.AlignCenter)
        self.statusLabel.setStyleSheet("color: #6B7280;")  # gray-500
        mainLayout.addWidget(self.statusLabel)

        # Processing phases frame
        phasesFrame = QFrame()
        phasesFrame.setObjectName("phasesFrame")
        phasesLayout = QVBoxLayout(phasesFrame)
        
        # Phases title
        phasesTitle = QLabel("Processing Phases")
        phasesTitle.setFont(QFont("Arial", 10, QFont.Bold))
        phasesLayout.addWidget(phasesTitle)
        
        # Phase indicators
        self.phases = [
            PhaseIndicator("Reading Data Files"),
            PhaseIndicator("Processing Test Data"),
            PhaseIndicator("Calculating Statistics"),
            PhaseIndicator("Generating Results")
        ]
        
        for phase in self.phases:
            phasesLayout.addWidget(phase)
        
        mainLayout.addWidget(phasesFrame)
        mainLayout.addStretch()
        mainLayout.setContentsMargins(40,40,40,40)
        # Initialize first phase
        self.phases[0].updateState(PhaseState.ACTIVE)
        
    def update_progress(self, value):
        """Update the progress indicators"""
        self.donutProgress.setPercentage(value)
        self.statusLabel.setText(f"Processing... {value}%")
        
        # Update phases based on progress
        if value >= 25:
            self.phases[0].updateState(PhaseState.COMPLETED)
            self.phases[1].updateState(PhaseState.ACTIVE)
        if value >= 50:
            self.phases[1].updateState(PhaseState.COMPLETED)
            self.phases[2].updateState(PhaseState.ACTIVE)
        if value >= 75:
            self.phases[2].updateState(PhaseState.COMPLETED)
            self.phases[3].updateState(PhaseState.ACTIVE)
        if value >= 100:
            self.phases[3].updateState(PhaseState.COMPLETED)
            self.statusLabel.setText("Processing completed!")
            self.cancelButton.setText("Done")
            self.cancelButton.setStyleSheet("""
                QPushButton {
                    background-color: #22C55E;  /* green-500 */
                }
                QPushButton:hover {
                    background-color: #16A34A;  /* green-600 */
                }
            """)

    def set_data(self, selected_items: list, files: list):
        """Set the data to be processed"""
        self.selected_items = selected_items
        self.files = files
        self.donutProgress.setPercentage(0)
        self.statusLabel.setText("Initializing...")
        self.start_processing()

    def start_processing(self):
        """Start the processing operation"""
        if hasattr(self, 'processor') and self.processor is not None:
            self.processor.terminate()
        
        self.processor = DataProcessor(self.selected_items, self.files)
        self.processor.progress.connect(self.update_progress)
        self.processor.finished.connect(self.processing_finished)
        self.processor.result.connect(self.handle_result)
        
        self.cancelButton.setText("Cancel")
        self.statusLabel.setText("Processing started...")
        self.processor.start()

    def cancel_processing(self):
        """Handle cancel button click"""
        if hasattr(self, 'processor') and self.processor and self.processor.isRunning():
            self.processor.terminate()
            self.processor = None
            self.statusLabel.setText("Processing cancelled")
            self.show_upload_signal.emit()
        else:
            self.show_upload_signal.emit()

    def handle_result(self, result_data):
        """Handle the processed data"""
        self.processed_data = result_data

    def processing_finished(self):
        """Handle completion of processing"""
        self.statusLabel.setText("Processing completed!")
        self.cancelButton.setText("Done")
        if self.processed_data is not None:
            self.show_results_signal.emit(self.processed_data)
        else:
            print("Warning: No processed data available")