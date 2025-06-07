from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, 
                             QLabel, QPushButton, QTableWidget, QTableWidgetItem,
                             QSplitter, QHeaderView, QScrollArea)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from ui.widgets.GaugeWidget import MetricWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns
import pandas as pd
from typing import List, Dict
import asyncio
import logging

logger = logging.getLogger(__name__)

class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=8, height=10, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

    def update_plot(self, data: List[Dict]):
        try:
            self.axes.clear()
            if not data:
                return
            
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            sns.set_style("whitegrid")
            sns.set_palette("husl")
            
            sns.lineplot(data=df, x='date', y='accuracy', label='Accuracy', marker='o', ax=self.axes)
            sns.lineplot(data=df, x='date', y='confidence', label='Confidence', marker='o', ax=self.axes)
            sns.lineplot(data=df, x='date', y='error_rate', label='Error Rate', marker='o', ax=self.axes)
            
            self.axes.set_xlabel('Date')
            self.axes.set_ylabel('Percentage (%)')
            self.axes.set_title('Model Performance Metrics')
            self.axes.tick_params(axis='x', rotation=45)
            self.axes.grid(True, linestyle='--', alpha=0.7)
            
            self.fig.tight_layout()
            self.draw()
        except Exception as e:
            logger.error(f"Error updating plot: {e}")

class MetricsTab(QWidget):
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
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

        # Header with just refresh button
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
        
        header_label = QLabel("Model Metrics Dashboard")
        header_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_label.setStyleSheet("color: #374151; border : none")
        
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
        header_layout.addWidget(refresh_btn)
        
        self.layout.addWidget(header_frame)

        # Gauges section
        self.metrics_layout = QHBoxLayout()
        self.layout.addLayout(self.metrics_layout)

        # Performance section
        performance_container = QFrame()
        performance_container.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
        """)
        performance_layout = QVBoxLayout(performance_container)
        performance_layout.setContentsMargins(15, 15, 15, 15)
        performance_layout.setSpacing(15)
        
        # Create splitter for plot and metrics table
        content_splitter = QVBoxLayout()

        # Left side - Plot
        plot_frame = QFrame()
        plot_frame.setFixedHeight(500)
        plot_layout = QVBoxLayout(plot_frame)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        self.plot_canvas = PlotCanvas(self)
        plot_layout.addWidget(self.plot_canvas)
        
        # Right side - Metrics table
        metrics_frame = QFrame()
        metrics_frame.setFixedHeight(300)
        metrics_layout = QVBoxLayout(metrics_frame)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        self.metrics_table = QTableWidget()
        metrics_layout.addWidget(self.metrics_table)
        
        content_splitter.addWidget(plot_frame)
        content_splitter.addWidget(metrics_frame)
        
        performance_layout.addLayout(content_splitter)
        self.layout.addWidget(performance_container)
        
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        self.load_metrics_data()

    def load_metrics_data(self):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        async def fetch_data():
            try:
                model_metrics = await self.api_client.get_model_metrics()
                self.update_model_metrics(model_metrics)
                self.update_performance_graph(model_metrics)
                self.update_metrics_table(model_metrics)
            except Exception as e:
                logger.error(f"Error fetching metrics: {e}")

        loop.run_until_complete(fetch_data())

    def update_model_metrics(self, metrics: List[Dict]):
        while self.metrics_layout.count():
            item = self.metrics_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not metrics:
            return

        latest = metrics[0]
        
        gauge_data = [
            {
                "title": "Model Accuracy",
                "value": latest.get('accuracy', 0) * 100,
                "threshold": {"good": 90, "moderate": 80}
            },
            {
                "title": "Confidence",
                "value": latest.get('confidence', 0) * 100,
                "threshold": {"good": 90, "moderate": 80}
            },
            {
                "title": "Error Rate",
                "value": latest.get('error_rate', 0) * 100,
                "threshold": {"good": 5, "moderate": 10}
            }
        ]

        for data in gauge_data:
            gauge = MetricWidget(data["title"], data["value"], data["threshold"])
            self.metrics_layout.addWidget(gauge)

    def update_performance_graph(self, metrics: List[Dict]):
        try:
            graph_data = []
            for metric in metrics:
                graph_data.append({
                    'date': metric.get('date', metric.get('created_at', '')).split('T')[0],
                    'accuracy': round(metric.get('accuracy', 0) * 100, 2),
                    'confidence': round(metric.get('confidence', 0) * 100, 2),
                    'error_rate': round(metric.get('error_rate', 0) * 100, 2)
                })
                
            self.plot_canvas.update_plot(graph_data)
        except Exception as e:
            logger.error(f"Error updating performance graph: {e}")

    def update_metrics_table(self, metrics: List[Dict]):
        try:
            self.metrics_table.clear()
            self.metrics_table.setRowCount(len(metrics))
            self.metrics_table.setColumnCount(5)
            self.metrics_table.setHorizontalHeaderLabels([
                "Date", "Accuracy", "Confidence", "Error Rate", "Status"
            ])

            for i, metric in enumerate(metrics):
                date = metric.get('date', metric.get('created_at', '')).split('T')[0]
                items = [
                    QTableWidgetItem(date),
                    QTableWidgetItem(f"{metric.get('accuracy', 0)*100:.2f}%"),
                    QTableWidgetItem(f"{metric.get('confidence', 0)*100:.2f}%"),
                    QTableWidgetItem(f"{metric.get('error_rate', 0)*100:.2f}%"),
                    QTableWidgetItem(metric.get('status', ''))
                ]
                
                for j, item in enumerate(items):
                    if j in [1, 2, 3]:  # Center align numeric columns
                        item.setTextAlignment(Qt.AlignCenter)
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