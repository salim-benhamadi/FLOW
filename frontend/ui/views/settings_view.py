
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QCheckBox, 
                               QMessageBox, QGraphicsDropShadowEffect,
                               QSlider)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from pathlib import Path
from api.settings_client import SettingsClient

def resource_path(relative_path):
    return str(Path(__file__).parent.parent.parent / relative_path)

class SettingPage(QWidget):
    show_upload_signal = Signal()
    show_select_signal = Signal()

    def __init__(self):
        super().__init__()
        self.api_client = SettingsClient()
        self.checkboxes = {}
        self.available_products = []
        self.sensitivity_value = 0.5
        self.initUI()
        self.load_available_products()
        self.load_settings()

    def initUI(self):
        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(20, 20, 20, 20)

        row1 = QHBoxLayout()
        settingTitle = QLabel("Configuration")
        settingTitle.setFont(QFont("Arial", 12, QFont.Bold))
        settingTitle.setStyleSheet("margin-bottom: 20px")
        row1.addWidget(settingTitle)

        buttonLayout = QHBoxLayout()
        self.saveButton = QPushButton("Save")
        self.saveButton.setStyleSheet("""
            QPushButton {
                background-color: #1849D6;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #1440A0;
            }
        """)
        self.saveButton.clicked.connect(self.save_and_navigate)

        self.backButton = QPushButton("Back")
        self.backButton.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #1849D6;
                border: 1px solid #1849D6;
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
        row1.setContentsMargins(0, 0, 0, 20)
        mainLayout.addLayout(row1)

        info_layout = QHBoxLayout()
        
        info_icon = QLabel()
        info_icon_pixmap = QPixmap(resource_path("./resources/icons/Info.png"))  
        info_icon_pixmap = info_icon_pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        info_icon.setPixmap(info_icon_pixmap)
        info_icon.setStyleSheet("border:none; min-height: none")
        info_layout.addWidget(info_icon)

        info_text = QLabel("Configure the reference products and sensitivity scale for distribution analysis. The sensitivity scale determines how strict the analysis should be.")
        info_text.setWordWrap(True)
        info_text.setTextFormat(Qt.RichText)
        info_text.setStyleSheet("border:none; min-height: none")
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
        refProductsLabel.setStyleSheet("background-color: #F8F9FE; min-height: 40px; border: 1px solid #DADEE8; border-top-left-radius: 5px; border-top-right-radius: 5px; margin: 0px; color: black; padding-left: 10px")
        mainLayout.setSpacing(0)
        mainLayout.addWidget(refProductsLabel)

        self.refProductsLayout = QVBoxLayout()
        self.refProductsContainer = QWidget()
        self.refProductsContainer.setLayout(self.refProductsLayout)
        self.refProductsContainer.setStyleSheet("border: 1px solid #DADEE8; border-top: none; border-bottom-left-radius: 5px; border-bottom-right-radius: 5px; padding: 10px;")
        mainLayout.addWidget(self.refProductsContainer)
        
        sensitivityLabel = QLabel("Sensitivity Scale")
        sensitivityLabel.setFont(QFont("Arial", 10))
        sensitivityLabel.setStyleSheet("background-color: #F8F9FE; min-height: 40px; border: 1px solid #DADEE8; border-top-left-radius: 5px; border-top-right-radius: 5px; margin: 0px; margin-top: 20px; color: black; padding-left: 10px")
        mainLayout.addWidget(sensitivityLabel)

        sensitivityLayout = QVBoxLayout()
        
        self.sensitivity_slider = QSlider(Qt.Horizontal)
        self.sensitivity_slider.setRange(0, 10)
        self.sensitivity_slider.setValue(5)
        self.sensitivity_slider.setTickPosition(QSlider.TicksBelow)
        self.sensitivity_slider.setTickInterval(1)
        self.sensitivity_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 8px;
                background: #E0E0E0;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #1849D6;
                border: 1px solid #1440A0;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::tick:horizontal {
                width: 2px;
                height: 10px;
                background: #999999;
            }
        """)
        self.sensitivity_slider.valueChanged.connect(self.on_sensitivity_changed)
        
        slider_labels_layout = QHBoxLayout()
        for i in range(11):
            label = QLabel(str(i/10))
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-size: 10px; color: #666666;")
            slider_labels_layout.addWidget(label)
        
        self.sensitivity_value_label = QLabel("Current value: 0.5")
        self.sensitivity_value_label.setAlignment(Qt.AlignCenter)
        self.sensitivity_value_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        
        sensitivityLayout.addWidget(self.sensitivity_slider)
        sensitivityLayout.addLayout(slider_labels_layout)
        sensitivityLayout.addWidget(self.sensitivity_value_label)

        sensitivityContainer = QWidget()
        sensitivityContainer.setLayout(sensitivityLayout)
        sensitivityContainer.setStyleSheet("border: 1px solid #DADEE8; border-top: none; border-bottom-left-radius: 5px; border-bottom-right-radius: 5px; padding: 20px;")
        
        mainLayout.addWidget(sensitivityContainer)
        mainLayout.addStretch()

    def on_sensitivity_changed(self, value):
        self.sensitivity_value = value / 10
        self.sensitivity_value_label.setText(f"Current value: {self.sensitivity_value}")

    def load_available_products(self):
        self.available_products = self.api_client.get_available_products()
        self.populate_product_checkboxes()

    def populate_product_checkboxes(self):
        for checkbox in self.checkboxes.values():
            checkbox.deleteLater()
        self.checkboxes.clear()
        
        if not self.available_products:
            no_products_label = QLabel("No reference products available. Please upload reference data first.")
            no_products_label.setStyleSheet("color: #666666; padding: 10px;")
            self.refProductsLayout.addWidget(no_products_label)
            return
        
        for product in self.available_products:
            checkbox = QCheckBox(product)
            checkbox.setStyleSheet("""
                QCheckBox {
                    border: none;
                    margin-bottom: 10px;
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
            checkbox.setChecked(True)
            self.checkboxes[product] = checkbox
            self.refProductsLayout.addWidget(checkbox)

    def save_and_navigate(self):
        self.save_settings()
        QMessageBox.information(self, "Configuration Saved", "Your settings have been successfully saved.", QMessageBox.Ok)
        self.emit_show_upload()
        self.emit_show_select()

    def save_settings(self):
        selected_products = [name for name, checkbox in self.checkboxes.items() if checkbox.isChecked()]
        
        validation_result = self.api_client.validate_settings(self.sensitivity_value, selected_products)
        if not validation_result.get('valid', False):
            QMessageBox.warning(self, "Validation Error", validation_result.get('message', 'Invalid settings'), QMessageBox.Ok)
            return
        
        success = self.api_client.update_settings(self.sensitivity_value, selected_products)
        if not success:
            QMessageBox.warning(self, "Save Error", "Could not save settings to server", QMessageBox.Ok)

    def load_settings(self):
        settings = self.api_client.get_settings()
        
        sensitivity = settings.get('sensitivity', 0.5)
        self.sensitivity_slider.setValue(int(sensitivity * 10))
        self.sensitivity_value = sensitivity
        self.sensitivity_value_label.setText(f"Current value: {sensitivity}")
        
        selected_products = settings.get('selected_products', [])
        for name, checkbox in self.checkboxes.items():
            checkbox.setChecked(name in selected_products)
    
    def emit_show_upload(self):
        self.show_upload_signal.emit()
    
    def emit_show_select(self):
        self.show_select_signal.emit()