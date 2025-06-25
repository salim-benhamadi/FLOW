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
        self.analysis_settings = {
            'sensitivity': 0.5,
            'model_version': 'v1'
        }
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

        settingsLabel = QLabel("")
        settingsLabel.setFont(QFont("Arial", 9))
        settingsLabel.setStyleSheet("color: #6B7280;")
        
        headerLayout.addWidget(backButton)
        headerLayout.addStretch()
        
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
        self.phases[0].updateState(PhaseState.ACTIVE)
        
        self.update_settings_display()
        
    def set_settings(self, settings: dict):
        self.analysis_settings = settings
        self.update_settings_display()
    
    def update_settings_display(self):
        sensitivity_pct = int(self.analysis_settings.get('sensitivity', 0.5) * 100)
        model_version = self.analysis_settings.get('model_version', 'v1')
        settings_text = f"Sensitivity: {sensitivity_pct}% | Model: {model_version}"
        
        for child in self.findChildren(QLabel):
            if child.styleSheet() and "color: #6B7280;" in child.styleSheet():
                child.setText(settings_text)
                break
        
    def update_progress(self, value):
        self.donutProgress.setPercentage(value)
        self.statusLabel.setText(f"Processing... {value}%")
        
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
                    background-color: #22C55E;
                }
                QPushButton:hover {
                    background-color: #16A34A;
                }
            """)

    def set_data(self, selected_items: list, files: list):
        self.selected_items = selected_items
        self.files = files
        self.donutProgress.setPercentage(0)
        self.statusLabel.setText("Initializing...")
        self.start_processing()

    def start_processing(self):
        if hasattr(self, 'processor') and self.processor is not None:
            self.processor.terminate()
        
        self.processor = DataProcessor(
            self.selected_items, 
            self.files,
            sensitivity=self.analysis_settings.get('sensitivity', 0.5),
            model_version=self.analysis_settings.get('model_version', 'v1')
        )
        self.processor.progress.connect(self.update_progress)
        self.processor.finished.connect(self.processing_finished)
        self.processor.result.connect(self.handle_result)
        self.processor.error.connect(self.handle_error)
        
        self.cancelButton.setText("Cancel")
        self.cancelButton.setStyleSheet("""
            QPushButton#cancelButton {
                background-color: #EF4444;
            }
            QPushButton#cancelButton:hover {
                background-color: #DC2626;
            }
        """)
        self.statusLabel.setText("Processing started...")
        self.processor.start()

    def cancel_processing(self):
        if hasattr(self, 'processor') and self.processor and self.processor.isRunning():
            self.processor.terminate()
            self.processor = None
            self.statusLabel.setText("Processing cancelled")
            self.show_upload_signal.emit()
        else:
            self.show_upload_signal.emit()

    def handle_result(self, result_data):
        self.processed_data = result_data

    def handle_error(self, error_message):
        self.statusLabel.setText(f"Error: {error_message}")
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
            self.show_results_signal.emit(self.processed_data)
        else:
            print("Warning: No processed data available")