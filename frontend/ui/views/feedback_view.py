
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame, 
                             QLabel, QPushButton, QTableWidget, QTableWidgetItem, 
                             QComboBox, QLineEdit, QToolButton)
from PySide6.QtCore import Qt, QSize
from ui.widgets.PlotDialog import PlotDialog
from ui.widgets.FeedbackApprovalDialog import FeedbackApprovalDialog
from PySide6.QtGui import QFont, QIcon, QColor, QBrush
import asyncio
import logging

logger = logging.getLogger(__name__)

class FeedbackMetricWidget(QFrame):
    def __init__(self, title, value):
        super().__init__()
        self.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 16px;
                border: 1px solid #e5e7eb;
                min-width: 150px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignCenter)
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 14, QFont.DemiBold))
        title_label.setStyleSheet("color: #374151; border: none")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        self.value_label = QLabel(str(value))
        self.value_label.setFont(QFont("Arial", 48, QFont.Bold))
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)
        
    def update_value(self, value):
        self.value_label.setText(str(value))
        
        # Set color based on the metric type and value
        color = self._get_color_for_value(value)
        self.value_label.setStyleSheet(f"color: {color}; border: none")
        
    def _get_color_for_value(self, value):
        # For Total Feedback - Blue shades
        if "Total" in self.layout().itemAt(0).widget().text():
            return "#1849D6"
        
        # For Pending Feedback - Yellow/Orange for higher numbers
        elif "Pending" in self.layout().itemAt(0).widget().text():
            if value > 50:
                return "#B88A00"  # Dark Orange
            elif value > 20:
                return "#F59E0B"  # Orange
            else:
                return "#10B981"  # Green
        
        # For Resolved Feedback - Green for higher numbers
        elif "Resolved" in self.layout().itemAt(0).widget().text():
            if value > 50:
                return "#059669"  # Dark Green
            elif value > 20:
                return "#10B981"  # Green
            else:
                return "#F59E0B"  # Orange


logger = logging.getLogger(__name__)

class FeedbackTab(QWidget):
    def __init__(self, feedback_client, input_client, reference_client):
        super().__init__()
        self.feedback_client = feedback_client
        self.input_client = input_client
        self.reference_client = reference_client
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)

        # Metrics section
        self.metrics_layout = QHBoxLayout()
        self.create_metrics_summary()
        layout.addLayout(self.metrics_layout)

        # Search and filter section
        search_frame = self.create_search_frame()
        layout.addWidget(search_frame)

        # Table
        self.feedback_table = QTableWidget()
        self.setup_feedback_table()
        layout.addWidget(self.feedback_table)

        self.load_feedback_data()

    def create_metrics_summary(self):
        self.total_feedback = FeedbackMetricWidget("Total Feedback", 0)
        self.pending_feedback = FeedbackMetricWidget("Pending Feedback", 0)
        self.resolved_feedback = FeedbackMetricWidget("Resolved Feedback", 0)
        
        self.metrics_layout.addWidget(self.total_feedback)
        self.metrics_layout.addWidget(self.pending_feedback)
        self.metrics_layout.addWidget(self.resolved_feedback)

    def create_search_frame(self):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                padding: 10px;
                border: 1px solid #e0e0e0;
            }
        """)
        
        layout = QHBoxLayout(frame)
        
        # Search container with blue background
        search_container = QFrame()
        search_container.setStyleSheet("""
            QFrame {
                background-color: rgba(24, 73, 214, 0.08);
                border-radius: 19px;
                padding: 5px 15px;
            }
        """)
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(10, 0, 10, 0)
        
        # Search icon
        search_icon = QToolButton()
        search_icon.setIcon(QIcon("./src/frontend/resources/icons/search.png"))
        search_icon.setIconSize(QSize(20, 20))
        search_icon.setStyleSheet("background: transparent; border: none;")
        
        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                padding: 5px;
                font-size: 14px;
                min-width: 200px;
            }
        """)
        self.search_input.textChanged.connect(self.on_search)
        
        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.search_input)
        
        # Filters
        severity_label = QLabel("Severity:")
        self.severity_filter = QComboBox()
        self.severity_filter.addItems(["All", "HIGH", "CRITICAL", "MEDIUM"])
        self.severity_filter.setStyleSheet("""
            QComboBox {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 5px;
                min-width: 120px;
            }
        """)
        
        status_label = QLabel("Status:")
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "PENDING", "IGNORED", "RESOLVED"])
        self.status_filter.setStyleSheet("""
            QComboBox {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 5px;
                min-width: 120px;
            }
        """)
        
        layout.addWidget(search_container)
        layout.addStretch(1)
        layout.addWidget(severity_label)
        layout.addWidget(self.severity_filter)
        layout.addWidget(status_label)
        layout.addWidget(self.status_filter)
        
        return frame

    def setup_feedback_table(self):
        columns = [
            "ID", "Severity", "Status", "Test Name", "Test Number", "Lot",
            "Insertion", "Initial Label", "New Label", "Reference ID",
            "Input ID", "Created At", "Updated At", "Actions"
        ]
        
        self.feedback_table.setColumnCount(len(columns))
        self.feedback_table.setHorizontalHeaderLabels(columns)
        
        # Set row height
        self.feedback_table.verticalHeader().setDefaultSectionSize(50)  # Set default row height to 50 pixels
        
        self.feedback_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #E5E7EB;
                gridline-color: #E5E7EB;
                background-color: white;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #E5E7EB;
            }
            QHeaderView::section {
                background-color: white;
                padding: 8px;
                border-bottom: 2px solid #E5E7EB;
                font-weight: bold;
                height: 50px;
            }
            QHeaderView::section:vertical {
                padding: 8px;
                height: 50px;
            }
        """)
        
        # Set column properties
        self.feedback_table.horizontalHeader().setStretchLastSection(True)
        self.feedback_table.verticalHeader().setVisible(False)
        self.feedback_table.setShowGrid(True)
        
        # Set actions column width
        actions_column = len(columns) - 1
        self.feedback_table.setColumnWidth(actions_column, 100)
        
        # Ensure the header height is also increased
        self.feedback_table.horizontalHeader().setFixedHeight(50)

    def run_async_task(self, coro):
        """Helper method to run async tasks"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(coro)

    def create_action_buttons(self, row):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)
        
        # View button
        view_btn = QToolButton()
        view_btn.setStyleSheet("""
            QToolButton {
                border: none;
                background-color: transparent;
                padding: 3px;
            }
            QToolButton:hover {
                background-color: #f0f0f0;
                border-radius: 4px;
            }
        """)
        view_btn.setText("👁️")  # Using emoji as fallback
        view_btn.setToolTip("View")
        view_btn.clicked.connect(lambda: self.run_async_task(self.view_feedback(row)))
        
        # Edit button
        edit_btn = QToolButton()
        edit_btn.setStyleSheet("""
            QToolButton {
                border: none;
                background-color: transparent;
                padding: 3px;
            }
            QToolButton:hover {
                background-color: #f0f0f0;
                border-radius: 4px;
            }
        """)
        edit_btn.setText("✏️")  # Using emoji as fallback
        edit_btn.setToolTip("Edit")
        edit_btn.clicked.connect(lambda: self.edit_feedback(row))
        
        try:
            view_btn.setIcon(QIcon("./src/frontend/resources/icons/Plot.png"))
            view_btn.setIconSize(QSize(20, 20))
            edit_btn.setIcon(QIcon("./src/frontend/resources/icons/edit.png"))
            edit_btn.setIconSize(QSize(20, 20))
        except:
            # If icons fail to load, we already have emoji fallbacks
            pass
        
        layout.addWidget(view_btn)
        layout.addWidget(edit_btn)
        layout.setAlignment(Qt.AlignCenter)
        
        return widget

    async def view_feedback(self, row):
        try:
            # Get the data from the selected row
            reference_id = self.feedback_table.item(row, 9).text()  # Reference ID column
            input_id = self.feedback_table.item(row, 10).text()     # Input ID column
            test_name = self.feedback_table.item(row, 3).text()     # Test Name column
            
            # Get input data measurements
            try:
                input_data = await self.input_client.get_input_data(input_id)
                if input_data:
                    input_measurements = input_data.get('measurements', [])
                    if isinstance(input_measurements, str):
                        # If measurements are stored as comma-separated string
                        input_measurements = [float(x) for x in input_measurements.split(',') if x.strip()]
                else:
                    input_measurements = []
            except Exception as e:
                logger.error(f"Error getting input data: {str(e)}")
                input_measurements = []

            # Get reference data measurements
            try:
                reference_data = await self.reference_client.get_reference_data(reference_id)
                if reference_data:
                    reference_measurements = reference_data.get('measurements', [])
                    if isinstance(reference_measurements, str):
                        # If measurements are stored as comma-separated string
                        reference_measurements = [float(x) for x in reference_measurements.split(',') if x.strip()]
                else:
                    reference_measurements = []
            except Exception as e:
                logger.error(f"Error getting reference data: {str(e)}")
                reference_measurements = []

            if input_measurements and reference_measurements:
                # Create and show plot dialog
                plot_dialog = PlotDialog(
                    input_data=input_measurements,
                    reference_data=reference_measurements,
                    test_name=test_name,
                    parent=self
                )
                plot_dialog.exec_()
            else:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "Data Error",
                    "Could not retrieve measurement data for plotting."
                )
                
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Error",
                f"Error viewing measurements: {str(e)}"
            )
            logger.error(f"Error in view_feedback: {str(e)}")

    def edit_feedback(self, row):
        """Show feedback approval dialog and update feedback status"""
        try:
            feedback_id = int(self.feedback_table.item(row, 0).text())  # Get feedback ID from first column
            test_name = self.feedback_table.item(row, 3).text()  # Get test name from fourth column
            
            # Create and show the approval dialog
            dialog = FeedbackApprovalDialog(feedback_id, test_name, self)
            result = dialog.exec_()
            
            if result > 0:  # Dialog was not cancelled
                # Get the appropriate status based on the dialog result
                new_status = "RESOLVED" if result == 1 else "IGNORED"
                
                # Update the status in the database
                loop = asyncio.get_event_loop()
                loop.run_until_complete(
                    self.feedback_client.update_feedback_status(feedback_id, new_status)
                )
                
                # Update the table cell with new status
                status_item = self.feedback_table.item(row, 2)  # Status is in third column
                status_item.setText(new_status)
                
                # Refresh the metrics
                self.load_feedback_data()
                
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Error",
                f"Error updating feedback status: {str(e)}"
            )
            logger.error(f"Error in edit_feedback: {str(e)}")

    def load_feedback_data(self):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        async def fetch_data():
            try:    
                feedback_data = await self.feedback_client.get_all_feedback()
                self.update_metrics(feedback_data)
                self.update_table(feedback_data)
            except Exception as e:
                logger.error(f"Error fetching feedback data: {e}")

        loop.run_until_complete(fetch_data())

    def update_metrics(self, feedback_response):
        feedback_data = feedback_response.get('data', [])
        
        total = len(feedback_data)
        pending = sum(1 for f in feedback_data if f.get('status') in ['PENDING', 'IGNORED'])
        resolved = sum(1 for f in feedback_data if f.get('status') == 'RESOLVED')
        
        self.total_feedback.update_value(total)
        self.pending_feedback.update_value(pending)
        self.resolved_feedback.update_value(resolved)

    def update_table(self, feedback_response):
        feedback_data = feedback_response.get('data', [])
        self.feedback_table.setRowCount(len(feedback_data))
        
        for row, feedback in enumerate(feedback_data):
            self.feedback_table.setItem(row, 0, QTableWidgetItem(str(feedback.get('id', ''))))
            self.feedback_table.setItem(row, 1, QTableWidgetItem(feedback.get('severity', '')))
            self.feedback_table.setItem(row, 2, QTableWidgetItem(feedback.get('status', '')))
            self.feedback_table.setItem(row, 3, QTableWidgetItem(feedback.get('test_name', '')))
            self.feedback_table.setItem(row, 4, QTableWidgetItem(feedback.get('test_number', '')))
            self.feedback_table.setItem(row, 5, QTableWidgetItem(feedback.get('lot', '')))
            self.feedback_table.setItem(row, 6, QTableWidgetItem(feedback.get('insertion', '')))
            self.feedback_table.setItem(row, 7, QTableWidgetItem(feedback.get('initial_label', '')))
            self.feedback_table.setItem(row, 8, QTableWidgetItem(feedback.get('new_label', '')))
            self.feedback_table.setItem(row, 9, QTableWidgetItem(feedback.get('reference_id', '')))
            self.feedback_table.setItem(row, 10, QTableWidgetItem(feedback.get('input_id', '')))
            self.feedback_table.setItem(row, 11, QTableWidgetItem(str(feedback.get('created_at', ''))))
            self.feedback_table.setItem(row, 12, QTableWidgetItem(str(feedback.get('updated_at', ''))))
            
            # Add action buttons
            self.feedback_table.setCellWidget(row, 13, self.create_action_buttons(row))
            
            # Style severity cells
            severity_item = self.feedback_table.item(row, 1)
            severity = feedback.get('severity', '')
            if severity == 'CRITICAL':
                severity_item.setForeground(QBrush(QColor("#DC2626")))
            elif severity == 'HIGH':
                severity_item.setForeground(QBrush(QColor("#F59E0B")))
            
        self.feedback_table.resizeColumnsToContents()

    def on_search(self, text):
        search_text = text.lower()
        for row in range(self.feedback_table.rowCount()):
            row_visible = False
            for col in range(self.feedback_table.columnCount() - 1):  # Exclude actions column
                item = self.feedback_table.item(row, col)
                if item and search_text in item.text().lower():
                    row_visible = True
                    break
            self.feedback_table.setRowHidden(row, not row_visible)