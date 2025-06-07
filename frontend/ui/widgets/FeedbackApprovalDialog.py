from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton)
from PySide6.QtCore import Qt

class FeedbackApprovalDialog(QDialog):
    def __init__(self, feedback_id, test_name, parent=None):
        super().__init__(parent)
        self.feedback_id = feedback_id
        self.initUI(test_name)
        
    def initUI(self, test_name):
        self.setWindowTitle("Feedback Review")
        self.setFixedSize(400, 150)
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton#approveButton {
                background-color: #10B981;
                color: white;
                border: none;
            }
            QPushButton#approveButton:hover {
                background-color: #059669;
            }
            QPushButton#declineButton {
                background-color: #EF4444;
                color: white;
                border: none;
            }
            QPushButton#declineButton:hover {
                background-color: #DC2626;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Message
        message = QLabel(f"Do you want to approve or decline the feedback for test '{test_name}'?")
        message.setWordWrap(True)
        message.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #374151;
                margin-bottom: 20px;
            }
        """)
        layout.addWidget(message)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        approve_button = QPushButton("Approve")
        approve_button.setObjectName("approveButton")
        approve_button.clicked.connect(self.approve)
        
        decline_button = QPushButton("Decline")
        decline_button.setObjectName("declineButton")
        decline_button.clicked.connect(self.decline)
        
        button_layout.addWidget(approve_button)
        button_layout.addWidget(decline_button)
        
        layout.addLayout(button_layout)
        
    def approve(self):
        self.done(1)  # 1 for approve
        
    def decline(self):
        self.done(2)  # 2 for decline