from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, 
                             QLabel, QPushButton, QTableWidget, QTableWidgetItem,
                             QSplitter, QHeaderView, QScrollArea, QComboBox,
                             QTabWidget, QTextEdit)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor
from ui.widgets.GaugeWidget import MetricWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
import pandas as pd
from typing import List, Dict
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=8, height=10, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

    def update_plot(self, data: List[Dict], show_versions=False):
        try:
            self.axes.clear()
            if not data:
                return
            
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            sns.set_style("whitegrid")
            sns.set_palette("husl")
            
            if show_versions and 'model_version' in df.columns:
                # Group by model version
                for version in df['model_version'].unique():
                    version_data = df[df['model_version'] == version]
                    sns.lineplot(data=version_data, x='date', y='accuracy', 
                               label=f'Accuracy ({version})', marker='o', ax=self.axes)
                    sns.lineplot(data=version_data, x='date', y='confidence', 
                               label=f'Confidence ({version})', marker='s', ax=self.axes)
                    sns.lineplot(data=version_data, x='date', y='error_rate', 
                               label=f'Error Rate ({version})', marker='^', ax=self.axes)
            else:
                sns.lineplot(data=df, x='date', y='accuracy', label='Accuracy', marker='o', ax=self.axes)
                sns.lineplot(data=df, x='date', y='confidence', label='Confidence', marker='o', ax=self.axes)
                sns.lineplot(data=df, x='date', y='error_rate', label='Error Rate', marker='o', ax=self.axes)
            
            self.axes.set_xlabel('Date')
            self.axes.set_ylabel('Percentage (%)')
            self.axes.set_title('Model Performance Metrics Over Time')
            self.axes.tick_params(axis='x', rotation=45)
            self.axes.grid(True, linestyle='--', alpha=0.7)
            self.axes.legend(loc='best', bbox_to_anchor=(1.05, 1))
            
            self.fig.tight_layout()
            self.draw()
        except Exception as e:
            logger.error(f"Error updating plot: {e}")

class VersionComparisonWidget(QWidget):
    """Widget to compare metrics across different model versions"""
    
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        
        # Version comparison plot
        self.comparison_canvas = PlotCanvas(self, width=10, height=6)
        layout.addWidget(self.comparison_canvas)
        
        # Version details table
        self.version_table = QTableWidget()
        self.version_table.setMaximumHeight(200)
        self.version_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                background-color: white;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 6px;
                border: 1px solid #e0e0e0;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.version_table)
    
    def update_version_comparison(self, version_data: List[Dict]):
        """Update the version comparison visualization"""
        try:
            if not version_data:
                return
            
            # Update plot
            self.comparison_canvas.axes.clear()
            
            versions = sorted(set(d['version'] for d in version_data))
            metrics = ['accuracy', 'confidence', 'error_rate']
            
            x = range(len(versions))
            width = 0.25
            
            for i, metric in enumerate(metrics):
                values = [next((d[metric] for d in version_data if d['version'] == v), 0) 
                         for v in versions]
                offset = width * (i - 1)
                self.comparison_canvas.axes.bar([xi + offset for xi in x], values, 
                                              width, label=metric.replace('_', ' ').title())
            
            self.comparison_canvas.axes.set_xlabel('Model Version')
            self.comparison_canvas.axes.set_ylabel('Percentage (%)')
            self.comparison_canvas.axes.set_title('Model Performance by Version')
            self.comparison_canvas.axes.set_xticks(x)
            self.comparison_canvas.axes.set_xticklabels(versions)
            self.comparison_canvas.axes.legend()
            self.comparison_canvas.axes.grid(True, axis='y', alpha=0.3)
            
            self.comparison_canvas.fig.tight_layout()
            self.comparison_canvas.draw()
            
            # Update table
            self.version_table.setColumnCount(6)
            self.version_table.setHorizontalHeaderLabels([
                "Version", "Created", "Accuracy", "Confidence", "Error Rate", "Training Data"
            ])
            self.version_table.setRowCount(len(version_data))
            
            for row, data in enumerate(version_data):
                self.version_table.setItem(row, 0, QTableWidgetItem(data['version']))
                self.version_table.setItem(row, 1, QTableWidgetItem(data.get('created_at', '')))
                self.version_table.setItem(row, 2, QTableWidgetItem(f"{data['accuracy']:.2f}%"))
                self.version_table.setItem(row, 3, QTableWidgetItem(f"{data['confidence']:.2f}%"))
                self.version_table.setItem(row, 4, QTableWidgetItem(f"{data['error_rate']:.2f}%"))
                self.version_table.setItem(row, 5, QTableWidgetItem(data.get('training_info', 'N/A')))
            
            self.version_table.resizeColumnsToContents()
            
        except Exception as e:
            logger.error(f"Error updating version comparison: {e}")

class MetricsTab(QWidget):
    """Enhanced metrics tab with VAMOS model version tracking"""
    
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
        self.current_version = "v1"
        self.model_versions = []
        self.initUI()
        
    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #f5f5f5;
            }
        """)

        scroll_content = QWidget()
        self.layout = QVBoxLayout(scroll_content)
        self.layout.setSpacing(20)
        self.layout.setContentsMargins(20, 20, 20, 20)

        # Enhanced header with version selector
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 8px;
                padding: 10px;
                border: 1px solid #e0e0e0;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 10, 10, 10)
        
        header_label = QLabel("VAMOS Model Metrics Dashboard")
        header_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_label.setStyleSheet("color: #374151; border: none")
        
        # Version selector
        version_layout = QHBoxLayout()
        version_label = QLabel("Model Version:")
        version_label.setStyleSheet("border: none; font-weight: bold;")
        
        self.version_selector = QComboBox()
        self.version_selector.setStyleSheet("""
            QComboBox {
                padding: 5px 10px;
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                min-width: 100px;
            }
        """)
        self.version_selector.currentTextChanged.connect(self.on_version_changed)
        
        version_layout.addWidget(version_label)
        version_layout.addWidget(self.version_selector)
        
        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        refresh_btn.clicked.connect(self.load_metrics_data)
        
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addLayout(version_layout)
        header_layout.addWidget(refresh_btn)
        
        self.layout.addWidget(header_frame)

        # Current version metrics (gauges)
        self.metrics_layout = QHBoxLayout()
        self.layout.addLayout(self.metrics_layout)

        # Create tabs for different views
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                background-color: white;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #f8f9fa;
                padding: 8px 15px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #1849D6;
            }
        """)
        
        # Performance History Tab
        performance_container = QWidget()
        performance_layout = QVBoxLayout(performance_container)
        performance_layout.setContentsMargins(15, 15, 15, 15)
        
        # Plot and metrics table
        plot_frame = QFrame()
        plot_frame.setFixedHeight(400)
        plot_layout = QVBoxLayout(plot_frame)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        self.plot_canvas = PlotCanvas(self)
        plot_layout.addWidget(self.plot_canvas)
        
        metrics_frame = QFrame()
        metrics_frame.setFixedHeight(250)
        metrics_layout = QVBoxLayout(metrics_frame)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        self.metrics_table = QTableWidget()
        metrics_layout.addWidget(self.metrics_table)
        
        performance_layout.addWidget(plot_frame)
        performance_layout.addWidget(metrics_frame)
        
        # Version Comparison Tab
        self.version_comparison = VersionComparisonWidget()
        
        # Training History Tab
        training_container = QWidget()
        training_layout = QVBoxLayout(training_container)
        training_layout.setContentsMargins(15, 15, 15, 15)
        
        self.training_history = QTextEdit()
        self.training_history.setReadOnly(True)
        self.training_history.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding: 10px;
                font-family: monospace;
                background-color: #f8f9fa;
            }
        """)
        training_layout.addWidget(self.training_history)
        
        # Add tabs
        self.tabs.addTab(performance_container, "Performance History")
        self.tabs.addTab(self.version_comparison, "Version Comparison")
        self.tabs.addTab(training_container, "Training Log")
        
        self.layout.addWidget(self.tabs)
        
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # Start auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.load_metrics_data)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
        
        self.load_metrics_data()

    def load_metrics_data(self):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        async def fetch_data():
            try:
                # Fetch model versions
                versions = await self.api_client.get_model_versions()
                self.update_version_selector(versions)
                
                # Fetch metrics for current version
                model_metrics = await self.api_client.get_model_metrics(version=self.current_version)
                self.update_model_metrics(model_metrics)
                self.update_performance_graph(model_metrics)
                self.update_metrics_table(model_metrics)
                
                # Fetch version comparison data
                version_metrics = await self.api_client.get_version_comparison_data()
                self.version_comparison.update_version_comparison(version_metrics)
                
                # Fetch training history
                training_log = await self.api_client.get_training_history()
                self.update_training_history(training_log)
                
            except Exception as e:
                logger.error(f"Error fetching metrics: {e}")

        loop.run_until_complete(fetch_data())

    def update_version_selector(self, versions: List[str]):
        """Update the version selector dropdown"""
        current_selection = self.version_selector.currentText()
        self.version_selector.clear()
        
        if versions:
            self.model_versions = sorted(versions, reverse=True)
            self.version_selector.addItems(self.model_versions)
            
            if current_selection in self.model_versions:
                self.version_selector.setCurrentText(current_selection)
            else:
                self.version_selector.setCurrentIndex(0)
                self.current_version = self.model_versions[0]

    def on_version_changed(self, version: str):
        """Handle version selection change"""
        if version and version != self.current_version:
            self.current_version = version
            self.load_metrics_data()

    def update_model_metrics(self, metrics: List[Dict]):
        """Update the gauge widgets with latest metrics"""
        while self.metrics_layout.count():
            item = self.metrics_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not metrics:
            return

        latest = metrics[0]
        
        # Add version indicator to gauges
        gauge_data = [
            {
                "title": f"Model Accuracy ({self.current_version})",
                "value": latest.get('accuracy', 0) * 100,
                "threshold": {"good": 90, "moderate": 80}
            },
            {
                "title": f"Confidence ({self.current_version})",
                "value": latest.get('confidence', 0) * 100,
                "threshold": {"good": 90, "moderate": 80}
            },
            {
                "title": f"Error Rate ({self.current_version})",
                "value": latest.get('error_rate', 0) * 100,
                "threshold": {"good": 5, "moderate": 10}
            },
            {
                "title": "VAMOS Score",
                "value": latest.get('vamos_score', 0) * 100,
                "threshold": {"good": 95, "moderate": 85}
            }
        ]

        for data in gauge_data:
            gauge = MetricWidget(data["title"], data["value"], data["threshold"])
            self.metrics_layout.addWidget(gauge)

    def update_performance_graph(self, metrics: List[Dict]):
        """Update the performance graph with version information"""
        try:
            graph_data = []
            for metric in metrics:
                graph_data.append({
                    'date': metric.get('date', metric.get('created_at', '')).split('T')[0],
                    'accuracy': round(metric.get('accuracy', 0) * 100, 2),
                    'confidence': round(metric.get('confidence', 0) * 100, 2),
                    'error_rate': round(metric.get('error_rate', 0) * 100, 2),
                    'model_version': metric.get('model_version', self.current_version)
                })
                
            self.plot_canvas.update_plot(graph_data, show_versions=True)
        except Exception as e:
            logger.error(f"Error updating performance graph: {e}")

    def update_metrics_table(self, metrics: List[Dict]):
        """Update the metrics table with version information"""
        try:
            self.metrics_table.clear()
            self.metrics_table.setRowCount(len(metrics))
            self.metrics_table.setColumnCount(7)
            self.metrics_table.setHorizontalHeaderLabels([
                "Date", "Version", "Accuracy", "Confidence", "Error Rate", "VAMOS Score", "Status"
            ])

            for i, metric in enumerate(metrics):
                date = metric.get('date', metric.get('created_at', '')).split('T')[0]
                items = [
                    QTableWidgetItem(date),
                    QTableWidgetItem(metric.get('model_version', self.current_version)),
                    QTableWidgetItem(f"{metric.get('accuracy', 0)*100:.2f}%"),
                    QTableWidgetItem(f"{metric.get('confidence', 0)*100:.2f}%"),
                    QTableWidgetItem(f"{metric.get('error_rate', 0)*100:.2f}%"),
                    QTableWidgetItem(f"{metric.get('vamos_score', 0)*100:.2f}%"),
                    QTableWidgetItem(metric.get('status', 'Active'))
                ]
                
                for j, item in enumerate(items):
                    if j in [2, 3, 4, 5]:  # Center align numeric columns
                        item.setTextAlignment(Qt.AlignCenter)
                    
                    # Color code based on VAMOS score
                    if j == 5:  # VAMOS Score column
                        vamos_score = metric.get('vamos_score', 0) * 100
                        if vamos_score >= 95:
                            item.setBackground(QColor("#d4edda"))
                        elif vamos_score >= 85:
                            item.setBackground(QColor("#fff3cd"))
                        else:
                            item.setBackground(QColor("#f8d7da"))
                    
                    self.metrics_table.setItem(i, j, item)

            self.metrics_table.setStyleSheet("""
                QTableWidget {
                    gridline-color: #e0e0e0;
                    background-color: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                }
                QHeaderView::section {
                    background-color: #f8f9fa;
                    padding: 6px;
                    border: 1px solid #e0e0e0;
                    font-weight: bold;
                }
                QTableWidget::item {
                    padding: 6px;
                }
            """)
            
            self.metrics_table.setAlternatingRowColors(True)
            self.metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.metrics_table.verticalHeader().setVisible(False)
            self.metrics_table.resizeColumnsToContents()
            
        except Exception as e:
            logger.error(f"Error updating metrics table: {e}")

    def update_training_history(self, training_log: List[Dict]):
        """Update the training history log"""
        try:
            log_text = "=== VAMOS Training History ===\n\n"
            
            for entry in training_log:
                timestamp = entry.get('timestamp', '')
                version = entry.get('version', '')
                event_type = entry.get('event_type', '')
                details = entry.get('details', {})
                
                log_text += f"[{timestamp}] Version: {version}\n"
                log_text += f"Event: {event_type}\n"
                
                if event_type == "AUTOMATIC_RETRAIN":
                    log_text += f"Trigger: VAMOS Analysis\n"
                    log_text += f"Confidence Score: {details.get('confidence', 0):.2f}%\n"
                    log_text += f"Matched Insertion: {details.get('insertion', 'N/A')}\n"
                    log_text += f"Matched Product: {details.get('product', 'N/A')}\n"
                elif event_type == "MANUAL_RETRAIN":
                    log_text += f"Trigger: Manual\n"
                    log_text += f"Initiated by: {details.get('user', 'Unknown')}\n"
                
                log_text += f"Training Duration: {details.get('duration', 'N/A')}\n"
                log_text += f"Final Accuracy: {details.get('accuracy', 0)*100:.2f}%\n"
                log_text += f"Status: {details.get('status', 'Unknown')}\n"
                log_text += "-" * 50 + "\n\n"
            
            self.training_history.setText(log_text)
            
        except Exception as e:
            logger.error(f"Error updating training history: {e}")

    def closeEvent(self, event):
        """Clean up resources on close"""
        self.refresh_timer.stop()
        event.accept()