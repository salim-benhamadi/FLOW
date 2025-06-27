from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLineEdit, QFrame, QMessageBox)
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtCore import Qt, Signal
from ui.utils.PathResources import resource_path

class LoginPage(QWidget):
    show_upload_signal = Signal()
    login_success_signal = Signal()
    
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QWidget {
                background-color: white;
            }
            QLineEdit {
                border: none;
                border-radius: 5px;
                background-color: #F0F0F0;
                padding: 12px;
                margin: 5px 20px;
                min-width: 300px;
                font-size: 14px;
            }
            QLineEdit:focus {
                background-color: #E8E8E8;
                border: 1px solid #1849D6;
            }
            QPushButton#loginBtn {
                background-color: #FF0000;
                color: white;
                border-radius: 5px;
                padding: 12px;
                min-width: 300px;
                margin: 15px 20px;
                font-size: 14px;
            }
            QPushButton#loginBtn:hover {
                background-color: #1238A3;
            }
            QPushButton#backBtn {
                background-color: transparent;
                color: #1849D6;
                border: none;
                text-align: left;
                padding: 5px;
                font-size: 14px;
            }
            QPushButton#backBtn:hover {
                color: #1238A3;
            }
        """)
        self.initUI()

    def initUI(self):
        self.setFixedWidth(530)
        self.setMinimumHeight(700)
        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(20, 20, 20, 20)
        mainLayout.setSpacing(15)
        mainLayout.setAlignment(Qt.AlignCenter)
        
        # Back button
        backButton = QPushButton("← Back")
        backButton.setObjectName("backBtn")
        backButton.clicked.connect(lambda: self.show_upload_signal.emit())
        
        topLayout = QHBoxLayout()
        topLayout.addWidget(backButton)
        topLayout.addStretch()
        mainLayout.addLayout(topLayout)
        
        # Login container
        loginContainer = QFrame()
        loginContainer.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        loginLayout = QVBoxLayout(loginContainer)
        loginLayout.setSpacing(20)
        
        # Logo
        logoLabel = QLabel()
        logoPixmap = QPixmap(resource_path('./resources/icons/SUPERVISOR.png'))
        logoPixmap = logoPixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logoLabel.setPixmap(logoPixmap)
        logoLabel.setAlignment(Qt.AlignCenter)
        
        # Input fields container
        inputsContainer = QFrame()
        inputsLayout = QVBoxLayout(inputsContainer)
        inputsLayout.setSpacing(15)
        
        # Username input
        usernameContainer = QVBoxLayout()
        self.usernameInput = QLineEdit()
        self.usernameInput.setPlaceholderText("Username")
        usernameContainer.addWidget(self.usernameInput)
        
        # Password input
        passwordContainer = QVBoxLayout()
        self.passwordInput = QLineEdit()
        self.passwordInput.setPlaceholderText("Password")
        self.passwordInput.setEchoMode(QLineEdit.Password)
        passwordContainer.addWidget(self.passwordInput)
        
        # Login button
        self.loginButton = QPushButton("Login")
        self.loginButton.setObjectName("loginBtn")
        self.loginButton.clicked.connect(self.handleLogin)
        
        # Add all elements to login layout
        loginLayout.addWidget(logoLabel)
        loginLayout.addLayout(usernameContainer)
        loginLayout.addLayout(passwordContainer)
        loginLayout.addWidget(self.loginButton)
        loginLayout.addStretch()
        
        # Add login container to main layout
        mainLayout.addWidget(loginContainer, 1)
        
    def handleLogin(self):
        username = self.usernameInput.text()
        password = self.passwordInput.text()
        
        if not username or not password:
            QMessageBox.warning(
                self,
                "Login Failed",
                "Please enter both username and password.",
                QMessageBox.Ok
            )
            return
        
        # Add your authentication logic here
        if username == "admin" and password == "admin":  # Replace with proper authentication
            self.clear()
            self.login_success_signal.emit()
        else:
            QMessageBox.warning(
                self,
                "Login Failed",
                "Invalid username or password. Please try again.",
                QMessageBox.Ok
            )
    
    def clear(self):
        """Clear input fields after successful login"""
        self.usernameInput.clear()
        self.passwordInput.clear()