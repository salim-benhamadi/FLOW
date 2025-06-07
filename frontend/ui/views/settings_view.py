from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, QGraphicsDropShadowEffect, 
                             QHBoxLayout, QCheckBox, QComboBox, QPushButton, QMessageBox)
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtCore import Qt, Signal
import json
import os

class SettingPage(QWidget):
    show_upload_signal = Signal()
    show_select_signal = Signal()
    
    def __init__(self):
        super().__init__()
        self.settings_file = "app_settings.json"
        self.checkboxes = {}
        self.core_model_combo = None
        self.initUI()
        self.load_settings()

    def initUI(self):
        self.setFixedWidth(480)
        self.setStyleSheet("background-color: white; color:black")
        mainLayout = QVBoxLayout(self)

        row1 = QHBoxLayout()
        
        titleLayout = QVBoxLayout()
        title = QLabel("Settings")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setStyleSheet("margin-bottom: 0px;")
        subtitle = QLabel("Select the configuration for the app")
        subtitle.setFont(QFont("Arial", 8))
        subtitle.setStyleSheet("color: gray; margin-left : 0px ; margin-top: 5px; margin-bottom: 20px;")
        
        titleLayout.addWidget(title)
        titleLayout.addWidget(subtitle)
        
        row1.addLayout(titleLayout)

        buttonLayout = QHBoxLayout()
        
        self.saveButton = QPushButton("Save")
        self.saveButton.setStyleSheet("""
            QPushButton {
                background-color: #23D74A; 
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
                margin-right : 5px;
            }
        """)
        self.saveButton.clicked.connect(self.save_and_navigate)
        
        self.backButton = QPushButton("Back")
        self.backButton.setStyleSheet("""
            QPushButton {
                background-color: #1849D6;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
            }
        """)
        
        buttonLayout.addWidget(self.saveButton, alignment=Qt.AlignRight)
        buttonLayout.addWidget(self.backButton, alignment=Qt.AlignRight)
        
        self.backButton.clicked.connect(self.emit_show_upload)
        self.backButton.clicked.connect(self.emit_show_select)
        row1.addStretch()
        row1.addLayout(buttonLayout)
        row1.setContentsMargins(0,0,0,20)
        mainLayout.addLayout(row1)

        info_layout = QHBoxLayout()
        
        info_icon = QLabel()
        info_icon_pixmap = QPixmap("./src/frontend/resources/icons/Info.png")  
        info_icon_pixmap = info_icon_pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        info_icon.setPixmap(info_icon_pixmap)
        info_icon.setStyleSheet("border:none; min-height : none")
        info_layout.addWidget(info_icon)

        info_text = QLabel("By default, all the available products are selected. We recommend keeping the <b>core model</b> settings unchanged as they are already optimized for the analysis purpose.")
        info_text.setWordWrap(True)
        info_text.setTextFormat(Qt.RichText)
        info_text.setStyleSheet("border:none; min-height : none")
        info_layout.addWidget(info_text, 1)

        info_widget = QWidget()
        info_widget.setLayout(info_layout)
        info_widget.setStyleSheet("""
            background-color: #E1F5FE;
            border: 1px solid #B3E5FC;
            border-radius: 5px;
            padding: 10px;
            color: #0277BD;
            min-height: 90px;
            margin-bottom: 10px;
        """)
        mainLayout.addWidget(info_widget)

        refProductsLabel = QLabel("Reference Products")
        refProductsLabel.setFont(QFont("Arial", 10))
        refProductsLabel.setStyleSheet("background-color: #F8F9FE; min-height :40px; border: 1px solid #DADEE8; border-top-left-radius: 5px; border-top-right-radius: 5px; margin: 0px; color: black; padding-left:10px")
        mainLayout.setSpacing(0)
        mainLayout.addWidget(refProductsLabel)

        refProductsLayout = QVBoxLayout()
        refProductsItems = ["Ajax", "Kairos", "MCLDp", "MultiRGB", "Orthus", "Tiny", "COMET"]
        for item in refProductsItems:
            checkbox = QCheckBox(item)
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
            if item == "Ajax":
                checkbox.setChecked(True)
            if item != "Ajax":
                checkbox.setEnabled(False)
                checkbox.setChecked(True)
            self.checkboxes[item] = checkbox
            refProductsLayout.addWidget(checkbox)

        refProductsContainer = QWidget()
        refProductsContainer.setLayout(refProductsLayout)
        refProductsContainer.setStyleSheet("border: 1px solid #DADEE8; border-top: none; border-bottom-left-radius: 5px; border-bottom-right-radius: 5px;")
        mainLayout.addWidget(refProductsContainer)
        
        coreModelLabel = QLabel("Core Model")
        coreModelLabel.setFont(QFont("Arial", 10))
        coreModelLabel.setStyleSheet("background-color: #F8F9FE; min-height :40px; border: 1px solid #DADEE8; border-top-left-radius: 5px; border-top-right-radius: 5px; margin: 0px;margin-top: 20px; color: black; padding-left:10px")
        mainLayout.addWidget(coreModelLabel)

        coreModelLayout = QVBoxLayout()

        self.core_model_combo = QComboBox()
        self.core_model_combo.addItems(["LightGBM", "Decision Tree", "Random Forest", "SVM", 
            "K-Nearest Neighbors", "Logistic Regression", "Chi-Square Test", "T-Test"])
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(0)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(0)
        self.core_model_combo.setGraphicsEffect(self.shadow)
        self.core_model_combo.setStyleSheet("border: 1px solid #9095A1; padding: 10px; border-radius: 4px; box-shadow: none;")
        coreModelLayout.addWidget(self.core_model_combo)

        coreModelContainer = QWidget()
        coreModelContainer.setLayout(coreModelLayout)
        coreModelContainer.setStyleSheet("border: 1px solid #DADEE8; border-top: none; border-bottom-left-radius: 5px; border-bottom-right-radius: 5px;")
        
        mainLayout.addWidget(coreModelContainer)
        mainLayout.addStretch()

    def save_and_navigate(self):
        self.save_settings()
        QMessageBox.information(self, "Configuration Saved", "Your settings have been successfully saved.", QMessageBox.Ok)
        self.emit_show_upload()
        self.emit_show_select()

    def save_settings(self):
        settings = {
            'reference_products': {
                name: checkbox.isChecked() 
                for name, checkbox in self.checkboxes.items()
            },
            'core_model': self.core_model_combo.currentText()
        }
        
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Could not save settings: {e}", QMessageBox.Ok)

    def load_settings(self):
        if not os.path.exists(self.settings_file):
            return
            
        try:
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
                
            for name, checked in settings.get('reference_products', {}).items():
                if name in self.checkboxes:
                    self.checkboxes[name].setChecked(checked)
                    
            core_model = settings.get('core_model')
            if core_model:
                index = self.core_model_combo.findText(core_model)
                if index >= 0:
                    self.core_model_combo.setCurrentIndex(index)
                    
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    def emit_show_upload(self):
        self.show_upload_signal.emit()
    
    def emit_show_select(self):
        self.show_select_signal.emit()