from PySide6.QtWidgets import (QMainWindow, QStackedWidget, QApplication, QWidget)
from PySide6.QtCore import QTimer
from ui.views.loading_view import LoadingPage
from ui.views.upload_view import UploadPage
from ui.views.settings_view import SettingPage
from ui.views.reference_selection_view import ReferenceSelectionPage
from ui.views.processing_view import ProcessingPage
from ui.views.select_view import SelectionPage
from ui.views.results_view import ResultPage
from ui.views.login_view import LoginPage
from ui.views.admin_view import AdminDashboard

class AppMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('VAMOS FLOW')
        self.setFixedWidth(500)
        self.setMinimumHeight(800)
        self.setContentsMargins(10, 10, 10, 0)
        self.setStyleSheet("background-color: white; color: black")
        
        # Initialize stacked widget
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Initialize all pages
        self.LoadingPage = LoadingPage()
        self.UploadPage = UploadPage()
        self.SettingPage = SettingPage()
        self.ReferenceSelectionPage = ReferenceSelectionPage()
        self.SelectionPage = SelectionPage()
        self.ProcessingPage = ProcessingPage()
        self.ResultPage = ResultPage()
        self.LoginPage = LoginPage()
        self.AdminDashboard = AdminDashboard()

        # Add pages to stack
        self.stack.addWidget(self.LoadingPage)
        self.stack.addWidget(self.UploadPage)
        self.stack.addWidget(self.SettingPage)
        self.stack.addWidget(self.ReferenceSelectionPage)
        self.stack.addWidget(self.SelectionPage)
        self.stack.addWidget(self.ProcessingPage)
        self.stack.addWidget(self.ResultPage)
        self.stack.addWidget(self.LoginPage)
        self.stack.addWidget(self.AdminDashboard)
        self.UploadPage.hide()
        
        QTimer.singleShot(3000, self.showSecondPage)

        self.connectSignals()

    def connectSignals(self):
        # Updated connections
        self.UploadPage.show_setting_signal.connect(self.show_settings)
        self.UploadPage.show_selection_signal.connect(self.show_reference_selection)  # Changed to show reference selection
        self.SettingPage.show_upload_signal.connect(self.show_upload)
        self.ReferenceSelectionPage.show_upload_signal.connect(self.show_upload)
        self.ReferenceSelectionPage.show_selection_signal.connect(self.show_selection)
        self.SelectionPage.show_upload_signal.connect(self.show_upload)
        self.SelectionPage.show_processing_signal.connect(self.show_processing)
        self.ProcessingPage.show_results_signal.connect(self.show_results)
        self.ProcessingPage.show_upload_signal.connect(self.show_upload)
        self.ResultPage.show_upload_signal.connect(self.show_upload)
        
        # Admin functionality connections
        self.UploadPage.show_admin_login_signal.connect(self.show_login)
        self.LoginPage.show_upload_signal.connect(self.show_upload)
        self.LoginPage.login_success_signal.connect(self.show_admin_dashboard)
        self.AdminDashboard.show_upload_signal.connect(self.reset_window_size)

    def reset_window_size(self):
        """Reset window size when returning to upload page"""
        self.setFixedWidth(500)
        self.setMinimumHeight(800)
        self.show_upload()

    def showSecondPage(self):
        """Show upload page after loading screen"""
        self.stack.setCurrentWidget(self.UploadPage)

    def show_settings(self):
        """Show settings page"""
        self.UploadPage.hide()
        self.stack.setCurrentWidget(self.SettingPage)
    
    def show_reference_selection(self, file_paths: list):
        """Show reference selection page with uploaded files"""
        self.ReferenceSelectionPage.set_uploaded_files(file_paths)
        self.setFixedWidth(600)  # Slightly wider for reference selection
        self.stack.setCurrentWidget(self.ReferenceSelectionPage)
    
    def show_selection(self, file_paths: list, reference_config: dict):
        """Show selection page with uploaded files and reference configuration"""
        self.SelectionPage.set_files(file_paths)
        self.SelectionPage.set_reference_config(reference_config)  # Pass reference config
        self.setFixedWidth(480)
        self.stack.setCurrentWidget(self.SelectionPage)
    
    def show_upload(self):
        """Show upload page"""
        self.setFixedWidth(500)  # Reset window size
        self.stack.setCurrentWidget(self.UploadPage)
    
    def show_processing(self, selected_items: list, files: list):
        """Show processing page"""
        self.ProcessingPage.set_data(selected_items, files)
        self.stack.setCurrentWidget(self.ProcessingPage)
    
    def show_results(self, data):
        """Show results page"""
        self.setFixedWidth(1200)
        self.ResultPage.populateTable(data)
        self.stack.setCurrentWidget(self.ResultPage)

    def show_login(self):
        """Show admin login page"""
        self.stack.setCurrentWidget(self.LoginPage)

    def show_admin_dashboard(self):
        self.setFixedWidth(1200)
        """Show admin dashboard after successful login"""
        self.stack.setCurrentWidget(self.AdminDashboard)

    def center_window(self):
        """Center the window on the screen"""
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        x = (screen.width() - size.width()) // 2
        y = (screen.height() - size.height()) // 2
        self.move(x, y)


if __name__ == "__main__":
    app = QApplication([])
    mainWindow = AppMainWindow()
    mainWindow.show()
    app.exec()