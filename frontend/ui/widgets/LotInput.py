from PySide6.QtWidgets import (QWidget, QHBoxLayout, QPushButton, QLineEdit)
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal

class LotInput(QWidget):
    deleted = Signal(object)
    
    def __init__(self, delete_icon, is_frontend=False, parent=None):
        super().__init__(parent)
        self.delete_icon = delete_icon
        self.is_frontend = is_frontend
        self.initUI()
        
    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if self.is_frontend:
            lot_layout = QHBoxLayout()
            self.input = QLineEdit()
            self.input.setPlaceholderText('Lot (e.g., ZA301387803)')
            self.input.setStyleSheet("border-radius: 5px; background-color: #F0F0F0; min-height: 30px; padding: 5px;")
            
            self.wafer_input = QLineEdit()
            self.wafer_input.setPlaceholderText('Wafer')
            self.wafer_input.setStyleSheet("border-radius: 5px; background-color: #F0F0F0; min-height: 30px; padding: 5px;")
            
            lot_layout.addWidget(self.input)
            lot_layout.addWidget(self.wafer_input)
            layout.addLayout(lot_layout)
        else:
            self.input = QLineEdit()
            self.input.setPlaceholderText('Lot (e.g., ZA301387803)')
            self.input.setStyleSheet("border-radius: 5px; background-color: #F0F0F0; min-height: 30px; padding: 5px;")
            layout.addWidget(self.input)
        
        self.deleteBtn = QPushButton()
        self.deleteBtn.setIcon(QIcon(self.delete_icon))
        self.deleteBtn.setFixedSize(30, 30)
        self.deleteBtn.setStyleSheet("QPushButton { border: none; }")
        self.deleteBtn.clicked.connect(lambda: self.deleted.emit(self))
        
        layout.addWidget(self.deleteBtn)