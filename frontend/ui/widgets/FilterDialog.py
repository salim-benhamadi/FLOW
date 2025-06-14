from PySide6.QtWidgets import (QLabel, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QDialogButtonBox, QDialog, QComboBox, QPushButton,
                             QScrollArea, QWidget, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
from ui.utils.PathResources import resource_path
class FilterCondition(QFrame):
    removed = Signal(object)
    
    def __init__(self, columns, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: #ffffff;
                margin: 4px;
                padding: 8px;
            }
            QFrame:hover {
                border-color: #bdbdbd;
                background-color: #fafafa;
            }
            QComboBox {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
                min-height: 25px;
            }
            QComboBox:hover {
                border-color: #1849D6;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }
            QLineEdit {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
                min-height: 25px;
            }
            QLineEdit:focus {
                border-color: #1849D6;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setSpacing(10)
        
        self.columnCombo = QComboBox()
        self.columnCombo.addItems(columns)
        self.columnCombo.setMinimumWidth(150)
        
        self.operatorCombo = QComboBox()
        self.operatorCombo.addItems(['contains', 'equals', 'starts with', 'ends with', 
                                   'greater than', 'less than', 'not equals'])
        self.operatorCombo.setMinimumWidth(120)
        
        self.valueEdit = QLineEdit()
        self.valueEdit.setPlaceholderText("Enter filter value")
        self.valueEdit.setMinimumWidth(200)
        
        self.removeButton = QPushButton()
        self.removeButton.setIcon(QIcon(resource_path('./resources/icons/remove.png')))
        self.removeButton.setFixedSize(28, 28)
        self.removeButton.setStyleSheet("""
            QPushButton {
                border: none;
                border-radius: 14px;
                padding: 4px;
                background-color: #f5f5f5;
            }
            QPushButton:hover {
                background-color: #ffebee;
            }
        """)
        self.removeButton.clicked.connect(lambda: self.removed.emit(self))
        
        layout.addWidget(self.columnCombo)
        layout.addWidget(self.operatorCombo)
        layout.addWidget(self.valueEdit)
        layout.addWidget(self.removeButton)
        layout.setContentsMargins(8, 8, 8, 8)

    def get_filter_values(self):
        return {
            'column': self.columnCombo.currentText(),
            'operator': self.operatorCombo.currentText(),
            'value': self.valueEdit.text()
        }

class FilterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Filter")
        self.setMinimumWidth(800)
        self.setMinimumHeight(400)
        
        self.columns = []
        if parent and hasattr(parent, 'table'):
            for i in range(parent.table.columnCount() - 1):
                header_item = parent.table.horizontalHeaderItem(i)
                if header_item:
                    self.columns.append(header_item.text())
        
        self.setStyleSheet("""
            QDialog {
                background-color: #fafafa;
            }
            QPushButton {
                padding: 8px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QLabel {
                color: #333333;
            }
            QScrollArea {
                background-color: transparent;
            }
            QWidget#filterContainer {
                background-color: transparent;
            }
        """)
        
        mainLayout = QVBoxLayout(self)
        mainLayout.setSpacing(15)
        
        headerLayout = QHBoxLayout()
        headerLayout.addStretch()
        scrollArea = QScrollArea()
        scrollArea.setWidgetResizable(True)
        scrollArea.setStyleSheet("QScrollArea { border: none; }")
        
        self.filterContainer = QWidget()
        self.filterContainer.setObjectName("filterContainer")
        self.filterLayout = QVBoxLayout(self.filterContainer)
        self.filterLayout.setSpacing(8)
        scrollArea.setWidget(self.filterContainer)
        
        self.conditions = []
        self.add_condition()
        
        addButton = QPushButton("Add Another Filter")
        addButton.setStyleSheet("""
            QPushButton {
                background-color: #1849D6;
                color: white;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2859E6;
            }
        """)
        addButton.clicked.connect(self.add_condition)
        
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        applyButton = buttonBox.button(QDialogButtonBox.Ok)
        cancelButton = buttonBox.button(QDialogButtonBox.Cancel)
        
        applyButton.setText("Apply Filters")
        applyButton.setStyleSheet("""
            QPushButton {
                background-color: #1FBE42;
                color: white;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #2FCE52;
            }
        """)
        
        cancelButton.setStyleSheet("""
            QPushButton {
                background-color: #f5f5f5;
                color: #333333;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        
        mainLayout.addLayout(headerLayout)
        mainLayout.addWidget(scrollArea)
        mainLayout.addWidget(addButton)
        mainLayout.addWidget(buttonBox)
        mainLayout.setContentsMargins(20, 20, 20, 20)

    def add_condition(self):
        condition = FilterCondition(self.columns)
        condition.removed.connect(self.remove_condition)
        self.conditions.append(condition)
        self.filterLayout.addWidget(condition)

    def remove_condition(self, condition):
        if len(self.conditions) > 1:
            self.conditions.remove(condition)
            condition.deleteLater()

    def get_filter_values(self):
        return [condition.get_filter_values() for condition in self.conditions]

def apply_filter(table, filter_conditions):
    def is_nan_value(value):
        """Check if a value represents NaN/null/empty"""
        if not value or value.strip() == '':
            return True
        value_lower = value.strip().lower()
        return value_lower in ['nan', 'null', 'none', 'n/a', '#n/a', '#null!', '#div/0!']
    
    def is_numeric_value(value):
        """Check if a value can be converted to a number and is not NaN"""
        if is_nan_value(value):
            return False
        try:
            num = float(value.strip())
            return not (num != num)  # Check for float('nan')
        except (ValueError, TypeError):
            return False
    
    for row in range(table.rowCount()):
        should_show = True
        
        if not filter_conditions:
            table.setRowHidden(row, False)
            continue
            
        for condition in filter_conditions:
            column_name = condition['column']
            operator = condition['operator']
            filter_value = condition['value']
            
            if not filter_value:
                continue
                
            column_index = -1
            for i in range(table.columnCount()):
                header_item = table.horizontalHeaderItem(i)
                if header_item and header_item.text() == column_name:
                    column_index = i
                    break
            
            if column_index == -1:
                continue
                
            item = table.item(row, column_index)
            if not item:
                should_show = False
                break
                
            cell_value = item.text().strip()
            filter_value = filter_value.strip()
            
            # Handle NaN values - exclude them from numeric comparisons
            if is_nan_value(cell_value):
                if operator in ['greater than', 'less than']:
                    should_show = False
                    break
                elif operator == 'equals':
                    # Only show NaN values if explicitly filtering for them
                    if not is_nan_value(filter_value):
                        should_show = False
                        break
                elif operator == 'not equals':
                    # NaN values should be shown only if not filtering for NaN
                    if is_nan_value(filter_value):
                        should_show = False
                        break
                elif operator in ['contains', 'starts with', 'ends with']:
                    # NaN values don't contain/start with/end with anything meaningful
                    should_show = False
                    break
                continue
            
            try:
                if operator == 'contains':
                    if filter_value.lower() not in cell_value.lower():
                        should_show = False
                        break
                elif operator == 'equals':
                    if filter_value.lower() != cell_value.lower():
                        should_show = False
                        break
                elif operator == 'starts with':
                    if not cell_value.lower().startswith(filter_value.lower()):
                        should_show = False
                        break
                elif operator == 'ends with':
                    if not cell_value.lower().endswith(filter_value.lower()):
                        should_show = False
                        break
                elif operator == 'greater than':
                    if is_numeric_value(cell_value) and is_numeric_value(filter_value):
                        if float(cell_value) <= float(filter_value):
                            should_show = False
                            break
                    else:
                        # For non-numeric comparisons, exclude if cell_value is not numeric
                        if not is_numeric_value(cell_value):
                            should_show = False
                            break
                        elif cell_value <= filter_value:
                            should_show = False
                            break
                elif operator == 'less than':
                    if is_numeric_value(cell_value) and is_numeric_value(filter_value):
                        if float(cell_value) >= float(filter_value):
                            should_show = False
                            break
                    else:
                        # For non-numeric comparisons, exclude if cell_value is not numeric
                        if not is_numeric_value(cell_value):
                            should_show = False
                            break
                        elif cell_value >= filter_value:
                            should_show = False
                            break
                elif operator == 'not equals':
                    if filter_value.lower() == cell_value.lower():
                        should_show = False
                        break
            except Exception as e:
                print(f"Error applying filter: {str(e)}")
                # On error, hide the row to be safe
                should_show = False
                break
        
        table.setRowHidden(row, not should_show)