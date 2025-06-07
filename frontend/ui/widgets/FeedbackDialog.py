from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QComboBox, QCheckBox)
from PySide6.QtCore import Qt
from datetime import datetime
class FeedbackDialog(QDialog):
    def __init__(self, current_status, test_name, test_number, lot, insertion, initial_label, 
                 reference_id, input_id, input_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Status")
        self.setModal(True)
        self.setFixedWidth(400)
        
        self.test_name = test_name
        self.test_number = test_number
        self.lot = lot
        self.insertion = insertion
        self.initial_label = initial_label
        self.reference_id = reference_id
        self.input_id = input_id
        self.input_data = input_data or {}
        
        layout = QVBoxLayout(self)
        
        status_layout = QHBoxLayout()
        status_label = QLabel("Status:")
        self.status_combo = QComboBox()
        self.status_combo.addItems([
            "Similar distribution",
            "Moderately similar",
            "Completely different"
        ])
        
        current_index = self.status_combo.findText(current_status)
        if current_index >= 0:
            self.status_combo.setCurrentIndex(current_index)
            
        status_layout.addWidget(status_label)
        status_layout.addWidget(self.status_combo)
        layout.addLayout(status_layout)

        self.feedback_checkbox = QCheckBox("Send as feedback")
        self.feedback_checkbox.stateChanged.connect(self.on_feedback_checked)
        layout.addWidget(self.feedback_checkbox)

        self.severity_layout = QHBoxLayout()
        severity_label = QLabel("Severity:")
        self.severity_combo = QComboBox()
        self.severity_combo.addItems([
            "CRITICAL",
            "HIGH",
            "MEDIUM"
        ])
        self.severity_combo.setCurrentText("MEDIUM")
        self.severity_layout.addWidget(severity_label)
        self.severity_layout.addWidget(self.severity_combo)
        layout.addLayout(self.severity_layout)
        
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        cancel_button = QPushButton("Cancel")
        self.save_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        # Set initial visibility of severity layout
        self.on_feedback_checked(Qt.Unchecked)

        self.severity_combo.setStyleSheet("""
            QComboBox[currentText="CRITICAL"] {
                color: red;
                font-weight: bold;
            }
            QComboBox[currentText="HIGH"] {
                color: orange;
                font-weight: bold;
            }
            QComboBox[currentText="MEDIUM"] {
                color: black;
            }
        """)

    def on_feedback_checked(self, state):
        is_checked = state == Qt.Checked
        for i in range(self.severity_layout.count()):
            widget = self.severity_layout.itemAt(i).widget()


    def get_values(self):
        new_status = self.status_combo.currentText()
        send_feedback = self.feedback_checkbox.isChecked()

        if send_feedback:
            # Create feedback data according to server's FeedbackData model
            feedback_data = {
                'severity': self.severity_combo.currentText(),
                'test_name': str(self.test_name),
                'test_number': str(self.test_number),
                'lot': str(self.lot) if self.lot else "",
                'insertion': str(self.insertion) if self.insertion else "",
                'initial_label': str(self.initial_label),
                'new_label': new_status,
                'reference_id': self.reference_id,
                'input_id': self.input_id
            }
            
            # Prepare input data
            input_data = {
                'input_id': str(self.input_id),
                'insertion': self.insertion,
                'test_name': self.test_name,
                'test_number': self.test_number,
                'lsl': self.input_data.get('lsl'),
                'usl': self.input_data.get('usl')
            }
            
            # Prepare measurements data
            measurements = []
            if 'input_data' in self.input_data and isinstance(self.input_data['input_data'], list):
                measurements = [
                    {
                        'chip_number': idx + 1,
                        'value': float(value) if value is not None else None
                    }
                    for idx, value in enumerate(self.input_data['input_data'])
                    if value is not None
                ]
            
            return {
                'new_status': new_status,
                'send_feedback': send_feedback,
                'feedback_data': feedback_data,
                'input_data': input_data,
                'measurements': measurements
            }
        else:
            return {
                'new_status': new_status,
                'send_feedback': send_feedback,
                'feedback_data': None,
                'input_data': None,
                'measurements': None
            }