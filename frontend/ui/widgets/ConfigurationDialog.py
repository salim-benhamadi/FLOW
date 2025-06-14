from PySide6.QtWidgets import (QDialog, QVBoxLayout, QCheckBox, 
                             QPushButton, QLabel, QScrollArea, QWidget,
                             QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt

class ConfigurationDialog(QDialog):
    def __init__(self, columns, visible_columns, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Table Configuration")
        self.setModal(True)
        self.setMinimumWidth(300)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout(self)
        
        label = QLabel("Select columns to display:")
        label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(label)
        
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        self.checkboxes = {}
        self.default_columns = ["Test Name", "Test Number", "Product", "Status",
                              "Mean", "Std"]
        
        # Remove ACTION from visible_columns temporarily
        self.visible_columns = [col for col in visible_columns if col != "ACTION"]
        
        # Filter out reference-related columns and ACTION
        filtered_columns = [col for col in columns if not (
            col.endswith('_reference') or 
            col in ['input_data', 'reference_data', 'ACTION'] or
            '_reference' in col
        )]
        
        # Sort columns to put default ones first
        sorted_columns = (
            self.default_columns + 
            [col for col in filtered_columns if col not in self.default_columns]
        )
        
        # Create checkboxes
        for column in sorted_columns:
            checkbox = QCheckBox(column)
            checkbox.setStyleSheet("""
                QCheckBox {
                    border : none;
                    margin-bottom : 10px;
                    }
                QCheckBox::indicator {
                    width: 15px;
                    height: 15px;
                    border: 1px solid #DADEE8;
                    border-radius: 5px;
                    background-color: white; 
                }
                QCheckBox::indicator:checked {
                    background-color: #1849D6;
                }
            """)
            if column in self.default_columns:
                checkbox.setChecked(True)
                checkbox.setEnabled(False)
                checkbox.setToolTip("This column cannot be hidden")
            else:
                checkbox.setChecked(column in self.visible_columns)
            
            self.checkboxes[column] = checkbox
            scroll_layout.addWidget(checkbox)
        
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        # Add buttons
        buttons_layout = QVBoxLayout()
        
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.accept)
        apply_button.setStyleSheet("""
            QPushButton {
                background-color: #1849D6;
                color: white;
                border-radius: 5px;
                padding: 8px 16px;
                margin-top: 10px;
            }
        """)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #808080;
                color: white;
                border-radius: 5px;
                padding: 8px 16px;
                margin-top: 5px;
            }
        """)
        
        buttons_layout.addWidget(apply_button)
        buttons_layout.addWidget(cancel_button)
        layout.addLayout(buttons_layout)
    
    def get_selected_columns(self):
        # Get selected columns
        selected = [col for col, checkbox in self.checkboxes.items() 
                   if checkbox.isChecked()]
        
        # Ensure default columns are included
        for col in self.default_columns:
            if col not in selected:
                selected.append(col)
        
        # Add ACTION as the last column (but don't add it twice)
        if "ACTION" not in selected:
            selected.append("ACTION")
        
        return selected