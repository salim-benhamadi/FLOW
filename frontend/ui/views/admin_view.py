from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, 
                               QLabel, QPushButton, QTableWidget, 
                               QTableWidgetItem, QComboBox, QDoubleSpinBox, QFrame, QTabBar)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QFont, QIcon, QPalette
import math
import asyncio
import logging
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

logger = logging.getLogger(__name__)

class ConnectionWorker(QThread):
    """Worker thread for checking cloud connection status"""
    connection_status_changed = Signal(bool, str)  # is_connected, status_message
    
    def __init__(self):
        super().__init__()
        self.api_client = None
        self.is_running = True
        
    def run(self):
        """Check connection status periodically"""
        while self.is_running:
            try:
                # Create a new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Test connection
                is_connected, message = loop.run_until_complete(self.check_connection())
                self.connection_status_changed.emit(is_connected, message)
                
                loop.close()
                
            except Exception as e:
                logger.error(f"Error in connection worker: {e}")
                self.connection_status_changed.emit(False, f"Connection error: {str(e)}")
            
            # Wait 30 seconds before next check
            self.msleep(30000)
    
    async def check_connection(self):
        """Async method to check cloud connection"""
        try:
            if self.api_client is None:
                self.api_client = APIClient()
            
            # Try to get health status
            health_data = await self.api_client.health_check()
            
            if health_data and health_data.get('status') == 'healthy':
                db_status = health_data.get('database', 'unknown')
                env = health_data.get('environment', 'unknown')
                return True, f"Connected to {env} environment (DB: {db_status})"
            else:
                return False, "Backend unhealthy"
                
        except Exception as e:
            return False, f"Offline: {str(e)}"
        finally:
            if self.api_client:
                try:
                    await self.api_client.close()
                    self.api_client = None
                except:
                    pass
    
    def stop(self):
        """Stop the worker thread"""
        self.is_running = False
        self.quit()
        self.wait(5000)  # Wait up to 5 seconds for thread to finish

        
class AdminDashboard(QWidget):
    show_upload_signal = Signal()  

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Admin Dashboard")
        self.setMinimumHeight(700)
        
        # Connection monitoring
        self.connection_worker = None
        self.is_connected = False
        self.connection_message = "Checking connection..."
        
        self.initUI()
        self.start_connection_monitoring()

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header section with improved spacing
        headerLayout = QHBoxLayout()
        titleLayout = QVBoxLayout()
        titleLayout.setSpacing(5)
        
        title = QLabel("Admin Dashboard")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: #2C3E50; margin-bottom: 0px;")
        
        subtitle = QLabel("Manage system settings and performance")
        subtitle.setFont(QFont("Arial", 10))
        subtitle.setStyleSheet("color: #7F8C8D; margin-top: 0px;")
        
        titleLayout.addWidget(title)
        titleLayout.addWidget(subtitle)
        
        # Status and navigation buttons
        buttonLayout = QHBoxLayout()
        buttonLayout.setSpacing(10)
        
        self.status = QPushButton("● Checking...")
        self.status.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #F39C12;
                border: 2px solid #F39C12;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(243, 156, 18, 0.1);
            }
        """)
        self.status.clicked.connect(self.manual_connection_check)
        
        self.backButton = QPushButton("← Back")
        self.backButton.setStyleSheet("""
            QPushButton {
                background-color: #1849D6;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #1640C4;
            }
            QPushButton:pressed {
                background-color: #1235A8;
            }
            QPushButton:disabled {
                background-color: #BDC3C7;
            }
        """)
        self.backButton.clicked.connect(lambda: self.show_upload_signal.emit())
        
        buttonLayout.addWidget(self.status)
        buttonLayout.addWidget(self.backButton)
        
        headerLayout.addLayout(titleLayout)
        headerLayout.addStretch()
        headerLayout.addLayout(buttonLayout)
        
        layout.addLayout(headerLayout)

        # Enhanced tab widget with modern styling
        tabs = self.createStyledTabWidget()
        tabs.addTab(self.createMetricsTab(), "📊 Analytics")
        tabs.addTab(self.createFeedbackTab(), "💬 Feedback")
        tabs.addTab(self.createRetrainingTab(), "🔄 Training")
        tabs.addTab(self.createSettingsTab(), "⚙️ Settings")
        
        layout.addWidget(tabs)

    def createStyledTabWidget(self):
        """Create a modern, styled tab widget"""
        tabs = QTabWidget()
        
        # Set tab position and shape
        tabs.setTabPosition(QTabWidget.North)
        tabs.setTabShape(QTabWidget.Rounded)
        
        # Apply comprehensive styling
        tabs.setStyleSheet("""
            QTabWidget {
                background-color: white;
                border: none;
            }
            
            QTabWidget::pane {
                border: 2px solid #E8E8E8;
                border-radius: 12px;
                background-color: white;
                margin-top: 0px;
                padding: 0px;
            }
            
            QTabWidget::tab-bar {
                alignment: left;
                border: none;
            }
            
            QTabBar::tab {
                background-color: #F8F9FA;
                color: #6C757D;
                padding: 12px 24px;
                margin-right: 4px;
                margin-bottom: 2px;
                border: 2px solid transparent;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                font-weight: 600;
                font-size: 12px;
                min-width: 120px;
            }
            
            QTabBar::tab:hover {
                background-color: #E9ECEF;
                color: #495057;
                border-color: #DEE2E6;
            }
            
            QTabBar::tab:selected {
                background-color: white;
                color: #1849D6;
                border-color: #E8E8E8;
                border-bottom-color: white;
                font-weight: bold;
            }
            
            QTabBar::tab:!selected {
                margin-top: 4px;
            }
            
            /* Remove tab focus outline */
            QTabBar::tab:focus {
                outline: none;
            }
        """)
        
        return tabs

    def createFeedbackTab(self):
        feedback_client = FeedbackClient()
        input_client = InputClient()
        reference_client = ReferenceClient()
        feedback_tab = FeedbackTab(feedback_client, input_client, reference_client)
        
        # Add container styling to tab content
        self.styleTabContent(feedback_tab)
        return feedback_tab

    def createRetrainingTab(self):
        api_client = APIClient()
        retrain_tab = RetrainingTab(api_client)
        
        # Add container styling to tab content
        self.styleTabContent(retrain_tab)
        return retrain_tab
    
    def createMetricsTab(self):
        api_client = MetricClient()
        metrics_tab = MetricsTab(api_client)
        
        # Add container styling to tab content
        self.styleTabContent(metrics_tab)
        return metrics_tab

    def createSettingsTab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Settings header
        headerLabel = QLabel("Configuration Settings")
        headerLabel.setFont(QFont("Arial", 14, QFont.Bold))
        headerLabel.setStyleSheet("color: #2C3E50; margin-bottom: 10px;")
        layout.addWidget(headerLabel)

        # Confidence Threshold Section
        thresholdFrame = self.createSettingsSection("Confidence Threshold", "Set the minimum confidence level for model predictions")
        thresholdLayout = thresholdFrame.layout()
        
        thresholdContainer = QHBoxLayout()
        thresholdLabel = QLabel("Threshold Value:")
        thresholdLabel.setFont(QFont("Arial", 10))
        
        thresholdSpinner = QDoubleSpinBox()
        thresholdSpinner.setRange(0.0, 1.0)
        thresholdSpinner.setSingleStep(0.05)
        thresholdSpinner.setValue(0.95)
        thresholdSpinner.setStyleSheet("""
            QDoubleSpinBox {
                border: 2px solid #E8E8E8;
                border-radius: 6px;
                padding: 8px;
                font-size: 11px;
                background-color: white;
            }
            QDoubleSpinBox:focus {
                border-color: #1849D6;
            }
        """)
        
        thresholdContainer.addWidget(thresholdLabel)
        thresholdContainer.addWidget(thresholdSpinner)
        thresholdContainer.addStretch()
        
        thresholdLayout.addLayout(thresholdContainer)
        layout.addWidget(thresholdFrame)

        # Feedback Weights Section
        weightsFrame = self.createSettingsSection("Feedback Weights", "Adjust the importance of different feedback types")
        weightsLayout = weightsFrame.layout()
        
        # Add weight adjustment controls
        weights = [
            ("Critical Issues", 2.0, "#E74C3C"),
            ("High Priority", 1.5, "#F39C12"), 
            ("Normal Priority", 1.0, "#27AE60")
        ]
        
        for label, default_value, color in weights:
            weightWidget = self.createWeightAdjuster(label, default_value, color)
            weightsLayout.addWidget(weightWidget)
        
        layout.addWidget(weightsFrame)
        
        # Add stretch to push content to top
        layout.addStretch()
        
        # Apply tab content styling
        self.styleTabContent(widget)
        return widget

    def createSettingsSection(self, title, description):
        """Create a styled settings section frame"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.NoFrame)
        frame.setStyleSheet("""
            QFrame {
                background-color: #FBFBFB;
                border: 1px solid #E8E8E8;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Section title
        titleLabel = QLabel(title)
        titleLabel.setFont(QFont("Arial", 12, QFont.Bold))
        titleLabel.setStyleSheet("color: #2C3E50;")
        
        # Section description
        descLabel = QLabel(description)
        descLabel.setFont(QFont("Arial", 9))
        descLabel.setStyleSheet("color: #7F8C8D;")
        descLabel.setWordWrap(True)
        
        layout.addWidget(titleLabel)
        layout.addWidget(descLabel)
        
        return frame

    def createWeightAdjuster(self, label, default_value, color):
        """Create an enhanced weight adjustment widget"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 8)
        
        # Color indicator
        indicator = QLabel("●")
        indicator.setStyleSheet(f"color: {color}; font-size: 16px;")
        
        # Label
        nameLabel = QLabel(label)
        nameLabel.setFont(QFont("Arial", 10))
        nameLabel.setMinimumWidth(120)
        
        # Spinner
        spinner = QDoubleSpinBox()
        spinner.setRange(0.0, 3.0)
        spinner.setSingleStep(0.1)
        spinner.setValue(default_value)
        spinner.setMinimumWidth(80)
        spinner.setStyleSheet("""
            QDoubleSpinBox {
                border: 2px solid #E8E8E8;
                border-radius: 6px;
                padding: 6px;
                font-size: 10px;
                background-color: white;
            }
            QDoubleSpinBox:focus {
                border-color: #1849D6;
            }
        """)
        
        # Value label
        valueLabel = QLabel(f"×{default_value}")
        valueLabel.setFont(QFont("Arial", 9))
        valueLabel.setStyleSheet("color: #7F8C8D;")
        valueLabel.setMinimumWidth(40)
        
        # Connect spinner to update value label
        spinner.valueChanged.connect(lambda value: valueLabel.setText(f"×{value:.1f}"))
        
        layout.addWidget(indicator)
        layout.addWidget(nameLabel)
        layout.addWidget(spinner)
        layout.addWidget(valueLabel)
        layout.addStretch()
        
        return widget

    def start_connection_monitoring(self):
        """Start monitoring cloud connection status"""
        try:
            self.connection_worker = ConnectionWorker()
            self.connection_worker.connection_status_changed.connect(self.update_connection_status)
            self.connection_worker.start()
            logger.info("Connection monitoring started")
        except Exception as e:
            logger.error(f"Failed to start connection monitoring: {e}")
            self.update_connection_status(False, "Connection monitoring failed")

    def update_connection_status(self, is_connected: bool, message: str):
        """Update the connection status button"""
        self.is_connected = is_connected
        self.connection_message = message
        
        if is_connected:
            self.status.setText("● Online")
            self.status.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #27AE60;
                    border: 2px solid #27AE60;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: rgba(39, 174, 96, 0.1);
                }
            """)
            self.status.setToolTip(f"Connected: {message}")
        else:
            self.status.setText("● Offline")
            self.status.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #E74C3C;
                    border: 2px solid #E74C3C;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: rgba(231, 76, 60, 0.1);
                }
            """)
            self.status.setToolTip(f"Offline: {message}")

    def manual_connection_check(self):
        """Manually trigger a connection check"""
        self.status.setText("● Checking...")
        self.status.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #F39C12;
                border: 2px solid #F39C12;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(243, 156, 18, 0.1);
            }
        """)
        self.status.setToolTip("Checking connection...")
        
        # The worker will automatically update the status

    def closeEvent(self, event):
        """Clean up when the widget is closed"""
        if self.connection_worker:
            self.connection_worker.stop()
            self.connection_worker = None
        event.accept()

    def styleTabContent(self, widget):
        """Apply consistent styling to tab content"""
        widget.setStyleSheet("""
            QWidget {
                background-color: white;
            }
        """)
        
        # Add padding to the main layout if it exists
        try:
            # Try to get layout as a method first
            layout = widget.layout()
            if layout is not None:
                layout.setContentsMargins(20, 20, 20, 20)
        except TypeError:
            # If layout is an attribute, not a method
            if hasattr(widget, 'layout') and widget.layout is not None:
                widget.layout.setContentsMargins(20, 20, 20, 20)