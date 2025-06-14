from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from ui.utils.PathResources import resource_path
class LoadingPage(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        self.setStyleSheet("background-color: white;")
        layout = QVBoxLayout()
        self.setLayout(layout)
        logo = QLabel(self)
        pixmap = QPixmap(resource_path('./resources/icons/VAMOS.png'))
        pixmap = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo.setPixmap(pixmap)
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)