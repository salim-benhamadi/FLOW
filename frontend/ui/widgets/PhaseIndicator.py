# File : processing.py
from PySide6.QtWidgets import (QWidget, QLabel, QHBoxLayout)
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QWidget, QLabel, QHBoxLayout)
from PySide6.QtGui import QFont
from enum import Enum

class PhaseState(Enum):
    PENDING = 0
    ACTIVE = 1
    COMPLETED = 2

class PhaseIndicator(QWidget):
    def __init__(self, phase_text, parent=None):
        super().__init__(parent)
        self.state = PhaseState.PENDING
        self.phase_text = phase_text
        
        # Create layout
        layout = QHBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 5, 0, 5)
        
        # Status indicator
        self.indicator = QLabel()
        self.indicator.setFixedSize(20, 20)
        
        # Phase text
        self.label = QLabel(phase_text)
        self.label.setFont(QFont("Arial", 10))
        self.label.setStyleSheet("background : transparent")
        layout.addWidget(self.indicator)
        layout.addWidget(self.label)
        layout.addStretch()
        
        self.updateState(PhaseState.PENDING)
    
    def updateState(self, state):
        self.state = state
        
        # Update indicator style
        if state == PhaseState.PENDING:
            self.indicator.setStyleSheet("""
                QLabel {
                    border: 2px solid #D1D5DB;
                    border-radius: 10px;
                    background-color: white;
                }
            """)
            self.label.setStyleSheet("color: #6B7280;")  # gray-500
        elif state == PhaseState.ACTIVE:
            self.indicator.setStyleSheet("""
                QLabel {
                    border: none;
                    border-radius: 10px;
                    background-color: #3B82F6;  /* blue-500 */
                    animation: spin 1s linear infinite;
                }
            """)
            self.label.setStyleSheet("color: #3B82F6;")  # blue-500
        else:  # COMPLETED
            self.indicator.setStyleSheet("""
                QLabel {
                    border: none;
                    border-radius: 10px;
                    background-color: #22C55E;  /* green-500 */
                }
            """)
            self.label.setStyleSheet("color: #22C55E;")  # green-500