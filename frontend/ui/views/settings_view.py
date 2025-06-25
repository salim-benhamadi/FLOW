from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox,
                               QSlider, QComboBox, QGroupBox, QMessageBox, QSpinBox,
                               QFrame)
from PySide6.QtGui import QFont, QIcon
from PySide6.QtCore import Qt, Signal, QTimer
import json
import os
import asyncio
from typing import List, Dict, Optional
from ui.utils.PathResources import resource_path
from api.settings_client import SettingsClient

class SettingsPage(QWidget):
    show_upload_signal = Signal()
    settings_changed_signal = Signal(dict)
    
    def __init__(self, api_client=SettingsClient):
        super().__init__()
        self.api_client = api_client
        self.model_versions = []
        self.current_settings = {
            'sensitivity': 0.5,
            'model_version': 'v1'
        }
        self.settings_file = "vamos_settings.json"
        self.initUI()
        self.load_settings()
        self.fetch_model_versions()

    def initUI(self):
        self.setFixedWidth(480)
        self.setMinimumHeight(600)
        self.setStyleSheet("background-color: white; color: black")
        
        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(40, 20, 40, 40)
        
        # Header Section
        self.setupHeaderSection(mainLayout)
        
        # Info Box
        self.setupInfoBox(mainLayout)
        
        # Sensitivity Settings
        self.setupSensitivitySection(mainLayout)
        
        # Model Version Settings
        self.setupModelVersionSection(mainLayout)
        
        mainLayout.addStretch()

    def setupHeaderSection(self, mainLayout):
        headerLayout = QHBoxLayout()
        
        titleLayout = QVBoxLayout()
        title = QLabel("Settings")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        title.setStyleSheet("margin-bottom: 0px;")
        
        subtitle = QLabel("Configure analysis sensitivity and model version")
        subtitle.setFont(QFont("Arial", 8))
        subtitle.setStyleSheet("color: gray; margin-top: 0px; margin-bottom: 20px;")
        
        titleLayout.addWidget(title)
        titleLayout.addWidget(subtitle)
        
        self.saveButton = QPushButton("Save")
        self.saveButton.setStyleSheet("""
            QPushButton {
                background-color: #23D74A;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
                margin-right: 5px;
            }
            QPushButton:hover {
                background-color: #1FBE42;
            }
        """)
        self.saveButton.clicked.connect(self.save_settings)
        
        self.backButton = QPushButton("Back")
        self.backButton.setStyleSheet("""
            QPushButton {
                background-color: #1849D6;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #1540B0;
            }
        """)
        self.backButton.clicked.connect(self.show_upload_signal.emit)
        
        headerLayout.addLayout(titleLayout)
        headerLayout.addStretch()
        headerLayout.addWidget(self.saveButton)
        headerLayout.addWidget(self.backButton)
        
        mainLayout.addLayout(headerLayout)

    def setupInfoBox(self, mainLayout):
        infoLayout = QHBoxLayout()
        
        infoIcon = QLabel()
        try:
            iconPath = resource_path('./resources/icons/Info.png')
            infoIcon.setPixmap(QPixmap(iconPath).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except:
            infoIcon.setText("ℹ")
            infoIcon.setFont(QFont("Arial", 16))
        infoIcon.setStyleSheet("border: none;")
        
        infoText = QLabel(
            "These settings control how the VAMOS tool analyzes distribution differences. "
            "Higher sensitivity will flag more subtle variations, while lower sensitivity "
            "focuses on major differences only."
        )
        infoText.setWordWrap(True)
        infoText.setStyleSheet("border: none; color: #0277BD;")
        
        infoLayout.addWidget(infoIcon)
        infoLayout.addWidget(infoText, 1)
        
        infoWidget = QWidget()
        infoWidget.setLayout(infoLayout)
        infoWidget.setStyleSheet("""
            background-color: #E1F5FE;
            border: 1px solid #B3E5FC;
            border-radius: 5px;
            padding: 10px;
            margin-bottom: 20px;
        """)
        
        mainLayout.addWidget(infoWidget)

    def setupSensitivitySection(self, mainLayout):
        sensitivityGroup = QGroupBox("Analysis Sensitivity")
        sensitivityGroup.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #E0E0E0;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        sensitivityLayout = QVBoxLayout()
        
        # Description
        descLabel = QLabel("Adjust how sensitive the analysis is to distribution differences:")
        descLabel.setWordWrap(True)
        descLabel.setStyleSheet("font-weight: normal; color: #666; margin-bottom: 10px;")
        sensitivityLayout.addWidget(descLabel)
        
        # Slider with labels
        sliderLayout = QVBoxLayout()
        
        # Slider
        self.sensitivitySlider = QSlider(Qt.Horizontal)
        self.sensitivitySlider.setMinimum(0)
        self.sensitivitySlider.setMaximum(10)
        self.sensitivitySlider.setValue(5)  # Default 0.5
        self.sensitivitySlider.setTickPosition(QSlider.TicksBelow)
        self.sensitivitySlider.setTickInterval(1)
        self.sensitivitySlider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #E0E0E0;
                height: 8px;
                background: #F0F0F0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #1849D6;
                border: 1px solid #1540B0;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #1540B0;
            }
        """)
        self.sensitivitySlider.valueChanged.connect(self.update_sensitivity_display)
        
        # Value display
        valueLayout = QHBoxLayout()
        self.sensitivityValueLabel = QLabel("0.5")
        self.sensitivityValueLabel.setFont(QFont("Arial", 12, QFont.Bold))
        self.sensitivityValueLabel.setStyleSheet("color: #1849D6;")
        
        self.sensitivityDescLabel = QLabel("(Balanced)")
        self.sensitivityDescLabel.setStyleSheet("color: #666; margin-left: 10px;")
        
        valueLayout.addWidget(QLabel("Current Value:"))
        valueLayout.addWidget(self.sensitivityValueLabel)
        valueLayout.addWidget(self.sensitivityDescLabel)
        valueLayout.addStretch()
        
        # Labels for slider
        labelLayout = QHBoxLayout()
        labelLayout.addWidget(QLabel("Low"))
        labelLayout.addStretch()
        labelLayout.addWidget(QLabel("Medium"))
        labelLayout.addStretch()
        labelLayout.addWidget(QLabel("High"))
        
        for i in range(labelLayout.count()):
            item = labelLayout.itemAt(i)
            if item and item.widget():
                item.widget().setStyleSheet("font-size: 10px; color: #888;")
        
        sliderLayout.addLayout(valueLayout)
        sliderLayout.addWidget(self.sensitivitySlider)
        sliderLayout.addLayout(labelLayout)
        
        sensitivityLayout.addLayout(sliderLayout)
        
        # Impact description
        self.impactLabel = QLabel()
        self.impactLabel.setWordWrap(True)
        self.impactLabel.setStyleSheet("font-weight: normal; color: #666; margin-top: 10px; padding: 10px; background-color: #F5F5F5; border-radius: 3px;")
        self.update_impact_description(5)
        sensitivityLayout.addWidget(self.impactLabel)
        
        sensitivityGroup.setLayout(sensitivityLayout)
        mainLayout.addWidget(sensitivityGroup)

    def setupModelVersionSection(self, mainLayout):
        modelGroup = QGroupBox("Model Version")
        modelGroup.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #E0E0E0;
                border-radius: 5px;
                margin-top: 20px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        modelLayout = QVBoxLayout()
        
        # Description
        modelDescLabel = QLabel("Select the model version to use for analysis:")
        modelDescLabel.setWordWrap(True)
        modelDescLabel.setStyleSheet("font-weight: normal; color: #666; margin-bottom: 10px;")
        modelLayout.addWidget(modelDescLabel)
        
        # Version selector
        versionLayout = QHBoxLayout()
        
        self.versionCombo = QComboBox()
        self.versionCombo.setStyleSheet("""
            QComboBox {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 8px;
                min-width: 200px;
                background-color: white;
            }
            QComboBox:hover {
                border-color: #1849D6;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(./resources/icons/arrow-down.png);
                width: 12px;
                height: 12px;
            }
        """)
        self.versionCombo.currentTextChanged.connect(self.on_version_changed)
        
        self.refreshButton = QPushButton("Refresh")
        self.refreshButton.setStyleSheet("""
            QPushButton {
                background-color: #F0F0F0;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
        """)
        self.refreshButton.clicked.connect(self.fetch_model_versions)
        
        versionLayout.addWidget(QLabel("Version:"))
        versionLayout.addWidget(self.versionCombo)
        versionLayout.addWidget(self.refreshButton)
        versionLayout.addStretch()
        
        modelLayout.addLayout(versionLayout)
        
        # Version info
        self.versionInfoLabel = QLabel("Loading available versions...")
        self.versionInfoLabel.setStyleSheet("font-weight: normal; color: #888; margin-top: 5px;")
        modelLayout.addWidget(self.versionInfoLabel)
        
        # Auto-update checkbox
        self.autoUpdateCheck = QCheckBox("Automatically use latest version")
        self.autoUpdateCheck.setStyleSheet("font-weight: normal; margin-top: 10px;")
        modelLayout.addWidget(self.autoUpdateCheck)
        
        modelGroup.setLayout(modelLayout)
        mainLayout.addWidget(modelGroup)

    def update_sensitivity_display(self, value):
        sensitivity = value / 10.0
        self.sensitivityValueLabel.setText(f"{sensitivity:.1f}")
        
        if sensitivity < 0.3:
            desc = "(Low - Major differences only)"
        elif sensitivity < 0.7:
            desc = "(Balanced)"
        else:
            desc = "(High - Subtle differences)"
        
        self.sensitivityDescLabel.setText(desc)
        self.update_impact_description(value)

    def update_impact_description(self, value):
        sensitivity = value / 10.0
        
        if sensitivity < 0.3:
            impact = "🟢 Low Sensitivity: Only major distribution differences will be flagged. " \
                    "Use this for stable processes where minor variations are expected."
        elif sensitivity < 0.7:
            impact = "🟡 Balanced Sensitivity: Moderate differences will be detected. " \
                    "Recommended for most use cases."
        else:
            impact = "🔴 High Sensitivity: Even subtle distribution changes will be flagged. " \
                    "Use this for critical processes requiring tight control."
        
        self.impactLabel.setText(impact)

    def on_version_changed(self, version):
        if version and version.startswith('v'):
            self.current_settings['model_version'] = version

    def fetch_model_versions(self):
        """Fetch available model versions from the cloud"""
        self.versionInfoLabel.setText("Fetching available versions...")
        self.refreshButton.setEnabled(False)
        
        if self.api_client:
            try:
                # Use synchronous call directly
                versions = self.api_client.get_model_versions()
                
                if versions:
                    self.update_version_list(versions)
                else:
                    self.use_default_versions()
            except Exception as e:
                print(f"Error fetching versions: {e}")
                self.use_default_versions()
        else:
            self.use_default_versions()
        
        self.refreshButton.setEnabled(True)

    def update_version_list(self, versions: List[str]):
        """Update the version combo box with fetched versions"""
        self.model_versions = versions
        current_selection = self.versionCombo.currentText()
        
        self.versionCombo.clear()
        self.versionCombo.addItems(versions)
        
        if current_selection in versions:
            self.versionCombo.setCurrentText(current_selection)
        elif self.current_settings.get('model_version') in versions:
            self.versionCombo.setCurrentText(self.current_settings['model_version'])
        
        latest = versions[0] if versions else "v1"
        self.versionInfoLabel.setText(f"Latest version: {latest}")

    def use_default_versions(self):
        """Use default versions when cloud fetch fails"""
        default_versions = ["v1", "v2", "v3"]
        self.update_version_list(default_versions)
        self.versionInfoLabel.setText("Using default versions (offline mode)")

    def save_settings(self):
        """Save current settings"""
        self.current_settings = {
            'sensitivity': self.sensitivitySlider.value() / 10.0,
            'model_version': self.versionCombo.currentText(),
            'auto_update': self.autoUpdateCheck.isChecked()
        }
        
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.current_settings, f, indent=4)
            
            self.settings_changed_signal.emit(self.current_settings)
            
            QMessageBox.information(
                self,
                "Settings Saved",
                "Your settings have been saved successfully.",
                QMessageBox.Ok
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                "Save Error",
                f"Could not save settings: {e}",
                QMessageBox.Ok
            )

    def load_settings(self):
        """Load saved settings"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
                
                # Apply sensitivity
                sensitivity = settings.get('sensitivity', 0.5)
                self.sensitivitySlider.setValue(int(sensitivity * 10))
                
                # Apply auto-update
                self.autoUpdateCheck.setChecked(settings.get('auto_update', False))
                
                self.current_settings = settings
                
            except Exception as e:
                print(f"Error loading settings: {e}")

    def get_settings(self) -> Dict:
        """Get current settings"""
        return {
            'sensitivity': self.sensitivitySlider.value() / 10.0,
            'model_version': self.versionCombo.currentText(),
            'auto_update': self.autoUpdateCheck.isChecked()
        }