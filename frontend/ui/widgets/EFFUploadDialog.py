from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFrame, QFileDialog)
from PySide6.QtCore import Qt

class EFFUploadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Upload Reference Data")
        self.setModal(True)
        self.setup_ui()
        self.file_path = None

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # File selection
        file_frame = QFrame()
        file_frame.setFrameStyle(QFrame.StyledPanel)
        file_layout = QHBoxLayout(file_frame)
        
        self.file_label = QLabel("Selected File: None")
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.browse_file)
        
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.browse_btn)
        layout.addWidget(file_frame)

        # Info frame
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.StyledPanel)
        info_layout = QVBoxLayout(info_frame)

        # Product
        product_layout = QHBoxLayout()
        product_label = QLabel("Product:")
        self.product_edit = QLineEdit()
        product_layout.addWidget(product_label)
        product_layout.addWidget(self.product_edit)
        info_layout.addLayout(product_layout)

        # Lot
        lot_layout = QHBoxLayout()
        lot_label = QLabel("Lot:")
        self.lot_edit = QLineEdit()
        lot_layout.addWidget(lot_label)
        lot_layout.addWidget(self.lot_edit)
        info_layout.addLayout(lot_layout)

        # Insertion
        insertion_layout = QHBoxLayout()
        insertion_label = QLabel("Insertion:")
        self.insertion_edit = QLineEdit()
        insertion_layout.addWidget(insertion_label)
        insertion_layout.addWidget(self.insertion_edit)
        info_layout.addLayout(insertion_layout)

        layout.addWidget(info_frame)

        # Buttons
        button_layout = QHBoxLayout()
        self.upload_btn = QPushButton("Upload")
        self.upload_btn.setEnabled(False)
        self.upload_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.upload_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)

        # Styling
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #ccc;
                border-radius: 5px;
                padding: 10px;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
            QPushButton {
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton#upload_btn {
                background-color: #28a745;
                color: white;
            }
            QPushButton#cancel_btn {
                background-color: #dc3545;
                color: white;
            }
        """)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select EFF File",
            "",
            "EFF Files (*.eff);;All Files (*)"
        )
        if file_path:
            self.file_path = file_path
            self.file_label.setText(f"Selected File: {file_path.split('/')[-1]}")
            self._check_can_upload()

    def _check_can_upload(self):
        can_upload = (
            self.file_path is not None and
            self.product_edit.text().strip() and
            self.lot_edit.text().strip() and
            self.insertion_edit.text().strip()
        )
        self.upload_btn.setEnabled(True)

    def get_data(self):
        return {
            'file_path': self.file_path,
            'product': self.product_edit.text().strip(),
            'lot': self.lot_edit.text().strip(),
            'insertion': self.insertion_edit.text().strip()
        }