from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
                               QLabel, QPushButton, QTableWidget, 
                               QTableWidgetItem, QComboBox, QDoubleSpinBox, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
import math
from ui.views.training_view import RetrainingTab
from api.client import APIClient
from api.metric_client import MetricClient
from ui.views.model_metrics_view import MetricsTab
from ui.views.feedback_view import FeedbackTab
from api.feedback_client import FeedbackClient
from api.input_client import InputClient
from api.reference_client import ReferenceClient
from ui.widgets.GaugeWidget import FeedbackMetricWidget, MetricWidget
import json

        
class AdminDashboard(QWidget):
    show_upload_signal = Signal()  

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Admin Dashboard")
        self.setMinimumHeight(700)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        # First row
        headerLayout = QHBoxLayout()
        titleLayout = QVBoxLayout()
        
        title = QLabel("Admin Dashboard")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setStyleSheet("margin-bottom: 0px;")
        subtitle = QLabel("Manage system settings and performance")
        subtitle.setFont(QFont("Arial", 8))
        subtitle.setStyleSheet("color: gray; margin-top: 0px; margin-bottom: 20px;")
        
        titleLayout.addWidget(title)
        titleLayout.addWidget(subtitle)
        
        self.backButton = QPushButton("Back")
        self.backButton.setStyleSheet("""
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
        self.backButton.clicked.connect(lambda: self.show_upload_signal.emit())
        
        headerLayout.addLayout(titleLayout)
        headerLayout.addStretch()
        headerLayout.addWidget(self.backButton, alignment=Qt.AlignRight)
                    
        self.status = QPushButton("Online")
        self.status.setStyleSheet("""
            QPushButton {
            background-color: transparent;
            color: green;
            border: 1px solid green;
            border-radius: 5px;
            padding: 5px 15px;
            margin-left: 5px;
            }
            QPushButton::inside {
            border: 1px solid green;
            }
        """)
        headerLayout.addWidget(self.status, alignment=Qt.AlignRight)
        headerLayout.addLayout(headerLayout)
        
        layout.addLayout(headerLayout)

        # Create tab widget
        tabs = QTabWidget()
        tabs.addTab(self.createMetricsTab(), "Metrics & Analytics")
        tabs.addTab(self.createFeedbackTab(), "Feedback Management")
        tabs.addTab(self.createRetrainingTab(), "Retraining Controls")
        tabs.addTab(self.createSettingsTab(), "Settings")
        
        layout.addWidget(tabs)

    def createFeedbackTab(self):
        feedback_client = FeedbackClient()
        input_client = InputClient()
        reference_client = ReferenceClient()
        feedback_tab = FeedbackTab(feedback_client, input_client, reference_client)
        return feedback_tab

    def createRetrainingTab(self):
        api_client = APIClient()
        retrain_tab = RetrainingTab(api_client)
        return retrain_tab
    
    def createMetricsTab(self):
        api_client = MetricClient()
        metrics_tab = MetricsTab(api_client)
        return metrics_tab

    def load_metrics_data(self):
        """Load training history from JSON file with error handling"""
        try:
            with open('training_history.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading training history: {e}")
            return {
                "latest_training": "2024-01-30",
                "history": [
                    {
                        "date": "2024-01-30",
                        "duration": "2h 15m",
                        "accuracy": 0.95,
                        "loss": 0.023,
                        "checkpoint_version": "v1.0.0"
                    }
                ]
            }

    def get_latest_metrics(self):
        """Get the most recent metrics with error handling"""
        try:
            return self.training_history["history"][0]
        except (KeyError, IndexError):
            return {
                "accuracy": 0.95,
                "loss": 0.023,
                "duration": "2h 15m",
                "checkpoint_version": "v1.0.0"
            }

    def refresh_metrics(self, layout):
        """Refresh metrics display"""
        self.training_history = self.load_metrics_data()
        # Clear and rebuild the metrics tab
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        # Recreate the metrics tab with new data
        self.createMetricsTab()

    def create_trend_chart(self, history):
        """Create trend visualization widget"""
        trend_widget = QWidget()
        trend_widget.setMinimumHeight(200)
        trend_widget.setStyleSheet("""
            background-color: #f8f9fa;
            border-radius: 8px;
            border: 1px dashed #d0d0d0;
        """)
        
        # Here you could add actual chart visualization
        # For now, using placeholder label
        chart_label = QLabel("Performance Graph\n(Trend visualization from training history)")
        chart_label.setAlignment(Qt.AlignCenter)
        
        layout = QVBoxLayout(trend_widget)
        layout.addWidget(chart_label)
        
        return trend_widget

    def populate_summary_table(self, table, history):
        """Populate the summary table with training history"""
        table.setRowCount(len(history))
        
        for i, entry in enumerate(history):
            table.setItem(i, 0, QTableWidgetItem(entry["date"]))
            table.setItem(i, 1, QTableWidgetItem(entry["duration"]))
            table.setItem(i, 2, QTableWidgetItem(f"{entry['accuracy']:.3f}"))
            table.setItem(i, 3, QTableWidgetItem(f"{entry['loss']:.3f}"))
            table.setItem(i, 4, QTableWidgetItem(entry.get("checkpoint_version", "N/A")))
        
        # Adjust column widths
        table.resizeColumnsToContents()

    def createSettingsTab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Confidence Threshold
        thresholdFrame = QFrame()
        thresholdFrame.setFrameStyle(QFrame.StyledPanel)
        thresholdLayout = QVBoxLayout(thresholdFrame)
        
        thresholdLabel = QLabel("Confidence Threshold")
        thresholdSpinner = QDoubleSpinBox()
        thresholdSpinner.setRange(0.0, 1.0)
        thresholdSpinner.setSingleStep(0.05)
        thresholdSpinner.setValue(0.95)
        
        thresholdLayout.addWidget(thresholdLabel)
        thresholdLayout.addWidget(thresholdSpinner)
        layout.addWidget(thresholdFrame)

        # Feedback Weights
        weightsFrame = QFrame()
        weightsFrame.setFrameStyle(QFrame.StyledPanel)
        weightsLayout = QVBoxLayout(weightsFrame)
        
        weightsLabel = QLabel("Feedback Weights")
        weightsLabel.setFont(QFont("Arial", 12, QFont.Bold))
        weightsLayout.addWidget(weightsLabel)
        
        # Add weight adjustment sliders
        criticalWeight = self.createWeightAdjuster("Critical Issues")
        highWeight = self.createWeightAdjuster("High Priority")
        normalWeight = self.createWeightAdjuster("Normal Priority")
        
        weightsLayout.addWidget(criticalWeight)
        weightsLayout.addWidget(highWeight)
        weightsLayout.addWidget(normalWeight)
        
        layout.addWidget(weightsFrame)

        return widget

    def createMetricWidget(self, title, value, color):
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        frame.setStyleSheet(f"QFrame {{ border: 2px solid {color}; border-radius: 5px; padding: 10px; }}")
        
        layout = QVBoxLayout(frame)
        
        titleLabel = QLabel(title)
        valueLabel = QLabel(value)
        valueLabel.setFont(QFont("Arial", 20, QFont.Bold))
        valueLabel.setStyleSheet(f"color: {color};")
        
        layout.addWidget(titleLabel)
        layout.addWidget(valueLabel)
        
        return frame

    def createWeightAdjuster(self, label):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        nameLabel = QLabel(label)
        spinner = QDoubleSpinBox()
        spinner.setRange(0.0, 2.0)
        spinner.setSingleStep(0.1)
        spinner.setValue(1.0)
        
        layout.addWidget(nameLabel)
        layout.addWidget(spinner)
        
        return widget

    def populateFeedbackTable(self):
        # Demo data - replace with real data
        feedbackData = [
            ("FB001", "Model Accuracy", "High", "Pending", "0.85", "2024-01-09"),
            ("FB002", "False Positive", "Critical", "In Review", "0.92", "2024-01-09"),
            ("FB003", "Data Quality", "Medium", "Resolved", "0.78", "2024-01-08"),
        ]
        
        self.feedbackTable.setRowCount(len(feedbackData))
        for i, row in enumerate(feedbackData):
            for j, item in enumerate(row):
                self.feedbackTable.setItem(i, j, QTableWidgetItem(str(item)))

    def populateStatusMessages(self):
        # Demo data - replace with real data
        statusData = [
            ("09:15:00", "Training Started", "Complete"),
            ("09:30:00", "Validation Phase", "In Progress"),
            ("09:45:00", "Model Evaluation", "Pending"),
        ]
        
        self.statusMessages.setRowCount(len(statusData))
        for i, row in enumerate(statusData):
            for j, item in enumerate(row):
                self.statusMessages.setItem(i, j, QTableWidgetItem(str(item)))