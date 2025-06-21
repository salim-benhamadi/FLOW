from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QRadioButton, 
                               QButtonGroup, QFileDialog, QMessageBox,
                               QLineEdit, QListWidget, QListWidgetItem,
                               QScrollArea, QTreeWidget, QTreeWidgetItem,
                               QFrame, QCheckBox, QGroupBox)
from PySide6.QtCore import Qt, Signal, QMimeData, QSize
from PySide6.QtGui import QFont, QPixmap, QDragEnterEvent, QDropEvent, QPainter, QBrush, QColor
import os
from pathlib import Path
from api.settings_client import SettingsClient
from api.reference_data_client import ReferenceDataClient
from ui.utils.PathResources import resource_path

class DragDropArea(QFrame):
    """Custom drag and drop area widget"""
    files_dropped = Signal(list)
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #1849D6;
                background-color: white;
                border-radius: 5px;
            }
        """)
        self.setFixedHeight(150)
        
        layout = QVBoxLayout(self)
        
        # Upload icon
        uploadIcon = QLabel()
        iconPixmap = QPixmap(resource_path('./resources/icons/upload.png'))
        iconPixmap = iconPixmap.scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        uploadIcon.setPixmap(iconPixmap)
        uploadIcon.setAlignment(Qt.AlignCenter)
        
        # Upload text
        uploadText = QLabel("Drag and drop reference files here")
        uploadText.setAlignment(Qt.AlignCenter)
        uploadText.setStyleSheet("color: #666666; border: none;")
        
        # Browse button
        self.browseButton = QPushButton("Browse Files")
        self.browseButton.setStyleSheet("""
            QPushButton {
                background-color: #1849D6;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
                border: none;
                max-width: 150px;
            }
            QPushButton:hover {
                background-color: #1440A0;
            }
        """)
        
        layout.addWidget(uploadIcon)
        layout.addWidget(uploadText)
        layout.addWidget(self.browseButton, alignment=Qt.AlignCenter)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith(('.eff', '.tsf', '.zip')):
                files.append(file_path)
        if files:
            self.files_dropped.emit(files)
        event.acceptProposedAction()

class FileItemWidget(QWidget):
    """Custom widget for file items matching upload page design"""
    remove_clicked = Signal(str)
    
    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.initUI()
    
    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # File icon
        iconLabel = QLabel()
        # Try to load file icon, fall back to a simple colored box if not found
        try:
            iconPixmap = QPixmap(resource_path('./resources/icons/file.png'))
            iconPixmap = iconPixmap.scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            iconLabel.setPixmap(iconPixmap)
        except:
            # Fallback: create a simple colored rectangle as file icon
            iconPixmap = QPixmap(30, 30)
            iconPixmap.fill(QColor("#1849D6"))
            iconLabel.setPixmap(iconPixmap)
            iconLabel.setStyleSheet("border-radius: 5px;")
        
        # File info layout
        infoLayout = QVBoxLayout()
        infoLayout.setSpacing(2)
        
        # File name
        fileName = QLabel(os.path.basename(self.file_path))
        fileName.setStyleSheet("font-weight: bold; color: #333333;")
        
        # File size
        file_size = os.path.getsize(self.file_path) / (1024 * 1024)  # Convert to MB
        sizeLabel = QLabel(f"{file_size:.2f} MB")
        sizeLabel.setStyleSheet("color: #666666; font-size: 10px;")
        
        infoLayout.addWidget(fileName)
        infoLayout.addWidget(sizeLabel)
        
        # Remove button
        removeBtn = QPushButton("✕")
        removeBtn.setFixedSize(25, 25)
        removeBtn.setStyleSheet("""
            QPushButton {
                background-color: #FF4444;
                color: white;
                border-radius: 12px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #CC0000;
            }
        """)
        removeBtn.clicked.connect(lambda: self.remove_clicked.emit(self.file_path))
        
        layout.addWidget(iconLabel)
        layout.addLayout(infoLayout)
        layout.addStretch()
        layout.addWidget(removeBtn)
        
        # Container styling
        self.setStyleSheet("""
            FileItemWidget {
                background-color: #F5F5F5;
                border-radius: 5px;
                margin: 2px;
            }
        """)

class ReferenceSelectionPage(QWidget):
    show_upload_signal = Signal()
    show_selection_signal = Signal(list, dict)  # files, reference_config
    
    def __init__(self):
        super().__init__()
        self.api_client = SettingsClient()
        self.reference_client = ReferenceDataClient()
        self.uploaded_files = []  # Files from upload page
        self.reference_files = []  # Reference files
        self.selected_products = []
        self.selected_lots = {}
        self.selected_insertions = {}
        self.initUI()
    
    def initUI(self):
        self.setFixedWidth(600)
        self.setMinimumHeight(800)
        self.setStyleSheet("background-color: white; color: black")
        
        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(20, 20, 20, 20)
        mainLayout.setSpacing(15)
        
        # Header
        self.setupHeader(mainLayout)
        
        # Reference data source selection
        self.setupReferenceSourceSelection(mainLayout)
        
        # Dynamic content area
        self.contentArea = QWidget()
        self.contentLayout = QVBoxLayout(self.contentArea)
        self.contentLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.addWidget(self.contentArea)
        
        # Initially show local upload interface
        self.showLocalUploadInterface()
        
        mainLayout.addStretch()
    
    def setupHeader(self, mainLayout):
        headerLayout = QHBoxLayout()
        
        # Title
        titleLayout = QVBoxLayout()
        title = QLabel("Reference Selection")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        subtitle = QLabel("Choose reference data for comparison")
        subtitle.setFont(QFont("Arial", 9))
        subtitle.setStyleSheet("color: gray;")
        
        titleLayout.addWidget(title)
        titleLayout.addWidget(subtitle)
        titleLayout.setSpacing(5)
        
        # Buttons
        buttonLayout = QHBoxLayout()
        
        self.backButton = QPushButton("Back")
        self.backButton.setStyleSheet("""
            QPushButton {
                background-color: #FFA500;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #FF8C00;
            }
        """)
        self.backButton.clicked.connect(self.go_back)
        
        self.proceedButton = QPushButton("Proceed")
        self.proceedButton.setStyleSheet("""
            QPushButton {
                background-color: #1849D6;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
            }
            QPushButton:disabled {
                background-color: grey;
            }
        """)
        self.proceedButton.setEnabled(False)
        self.proceedButton.clicked.connect(self.proceed)
        
        buttonLayout.addWidget(self.backButton)
        buttonLayout.addWidget(self.proceedButton)
        
        headerLayout.addLayout(titleLayout)
        headerLayout.addStretch()
        headerLayout.addLayout(buttonLayout)
        
        mainLayout.addLayout(headerLayout)
    
    def setupReferenceSourceSelection(self, mainLayout):
        groupBox = QGroupBox("Reference Data Source")
        groupBox.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #DADEE8;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: white;
            }
        """)
        
        groupLayout = QVBoxLayout(groupBox)
        
        self.sourceGroup = QButtonGroup()
        
        self.localRadio = QRadioButton("I have reference data locally")
        self.localRadio.setChecked(True)
        self.localRadio.toggled.connect(self.onSourceChanged)
        
        self.cloudRadio = QRadioButton("Use reference data from cloud")
        self.cloudRadio.toggled.connect(self.onSourceChanged)
        
        self.sourceGroup.addButton(self.localRadio)
        self.sourceGroup.addButton(self.cloudRadio)
        
        groupLayout.addWidget(self.localRadio)
        groupLayout.addWidget(self.cloudRadio)
        
        mainLayout.addWidget(groupBox)
    
    def onSourceChanged(self):
        # Clear the content area
        while self.contentLayout.count():
            child = self.contentLayout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        if self.localRadio.isChecked():
            self.showLocalUploadInterface()
        else:
            self.showCloudSelectionInterface()
    
    def showLocalUploadInterface(self):
        # Drag and drop area
        self.dragDropArea = DragDropArea()
        self.dragDropArea.files_dropped.connect(self.addReferenceFiles)
        self.dragDropArea.browseButton.clicked.connect(self.browseFiles)
        self.contentLayout.addWidget(self.dragDropArea)
        
        # Files section with same design as upload page
        filesSection = QWidget()
        filesSection.setStyleSheet("""
            QWidget {
                background-color: #F8F9FA;
                border-radius: 5px;
                padding: 10px;
                margin-top: 10px;
            }
        """)
        filesSectionLayout = QVBoxLayout(filesSection)
        
        # Files header
        filesHeader = QHBoxLayout()
        filesLabel = QLabel("Selected Reference Files")
        filesLabel.setFont(QFont("Arial", 10, QFont.Bold))
        filesLabel.setStyleSheet("background-color: transparent;")
        
        self.fileCountLabel = QLabel("(0 files)")
        self.fileCountLabel.setStyleSheet("color: #666666; background-color: transparent;")
        
        filesHeader.addWidget(filesLabel)
        filesHeader.addWidget(self.fileCountLabel)
        filesHeader.addStretch()
        
        filesSectionLayout.addLayout(filesHeader)
        
        # Files container
        self.filesContainer = QWidget()
        self.filesContainerLayout = QVBoxLayout(self.filesContainer)
        self.filesContainerLayout.setContentsMargins(0, 5, 0, 0)
        self.filesContainerLayout.setSpacing(5)
        
        # Scroll area for files
        scrollArea = QScrollArea()
        scrollArea.setWidget(self.filesContainer)
        scrollArea.setWidgetResizable(True)
        scrollArea.setMaximumHeight(300)
        scrollArea.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        filesSectionLayout.addWidget(scrollArea)
        
        self.contentLayout.addWidget(filesSection)
        
        # Update display
        self.updateFileDisplay()
        self.updateProceedButton()
    
    def showCloudSelectionInterface(self):
        # Search bar
        searchLayout = QHBoxLayout()
        searchLabel = QLabel("Search:")
        self.searchInput = QLineEdit()
        self.searchInput.setPlaceholderText("Search products, lots, or insertions...")
        self.searchInput.setStyleSheet("""
            QLineEdit {
                border: 1px solid #DADEE8;
                border-radius: 5px;
                padding: 5px;
                min-height: 25px;
            }
        """)
        self.searchInput.textChanged.connect(self.filterCloudData)
        
        searchLayout.addWidget(searchLabel)
        searchLayout.addWidget(self.searchInput)
        self.contentLayout.addLayout(searchLayout)
        
        # Products tree
        productsLabel = QLabel("Available Products:")
        productsLabel.setFont(QFont("Arial", 10, QFont.Bold))
        productsLabel.setStyleSheet("margin-top: 10px;")
        self.contentLayout.addWidget(productsLabel)
        
        self.productsTree = QTreeWidget()
        self.productsTree.setHeaderHidden(True)
        self.productsTree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #DADEE8;
                border-radius: 5px;
                padding: 5px;
            }
            QTreeWidget::item {
                padding: 3px;
            }
            QTreeWidget::item:selected {
                background-color: #1849D6;
                color: white;
            }
            QTreeWidget::indicator {
                width: 15px;
                height: 15px;
            }
            QTreeWidget::indicator:unchecked {
                border: 1px solid #DADEE8;
                background-color: white;
                border-radius: 3px;
            }
            QTreeWidget::indicator:checked {
                background-color: #1849D6;
                border: 1px solid #1849D6;
                border-radius: 3px;
            }
            QTreeWidget::indicator:checked::after {
                position: absolute;
                width: 5px;
                height: 10px;
                border: solid white;
                border-width: 0 2px 2px 0;
                top: 2px;
                left: 5px;
            }
        """)
        self.productsTree.itemChanged.connect(self.onCloudSelectionChanged)
        
        scrollArea = QScrollArea()
        scrollArea.setWidget(self.productsTree)
        scrollArea.setWidgetResizable(True)
        scrollArea.setMaximumHeight(400)
        self.contentLayout.addWidget(scrollArea)
        
        # Load cloud data
        self.loadCloudData()
    
    def loadCloudData(self):
        """Load available products from cloud"""
        self.productsTree.clear()
        
        # Show loading message
        loadingItem = QTreeWidgetItem(self.productsTree, ["Loading reference data..."])
        self.productsTree.addTopLevelItem(loadingItem)
        
        try:
            # Fetch data from API using the correct method
            data = self.reference_client.get_reference_data_structure()
            
            # Clear loading message
            self.productsTree.clear()
            
            products = data.get("products", {})
            
            if not products:
                noDataItem = QTreeWidgetItem(self.productsTree, ["No reference data available in cloud"])
                self.productsTree.addTopLevelItem(noDataItem)
                QMessageBox.information(self, "No Data", "No reference data is currently available in the cloud. Please upload reference data locally or contact your administrator.")
                return
            
            for product, product_data in products.items():
                productItem = QTreeWidgetItem(self.productsTree, [product])
                productItem.setFlags(productItem.flags() | Qt.ItemIsUserCheckable)
                productItem.setCheckState(0, Qt.Unchecked)
                
                lots = product_data.get("lots", {})
                for lot, insertions in lots.items():
                    lotItem = QTreeWidgetItem(productItem, [lot])
                    lotItem.setFlags(lotItem.flags() | Qt.ItemIsUserCheckable)
                    lotItem.setCheckState(0, Qt.Unchecked)
                    
                    for insertion in insertions:
                        insertionItem = QTreeWidgetItem(lotItem, [insertion])
                        insertionItem.setFlags(insertionItem.flags() | Qt.ItemIsUserCheckable)
                        insertionItem.setCheckState(0, Qt.Unchecked)
            
            self.productsTree.expandAll()
            
        except Exception as e:
            # Clear loading message
            self.productsTree.clear()
            
            # Show error message
            errorItem = QTreeWidgetItem(self.productsTree, ["Error loading reference data"])
            self.productsTree.addTopLevelItem(errorItem)
            
            QMessageBox.critical(
                self, 
                "Connection Error", 
                f"Failed to load reference data from cloud:\n{str(e)}\n\nPlease check your connection or use local reference data."
            )
    
    def filterCloudData(self, text):
        """Filter tree based on search text"""
        def setItemVisibility(item, text):
            text = text.lower()
            item_text = item.text(0).lower()
            match = text in item_text
            
            # Check children
            child_match = False
            for i in range(item.childCount()):
                child = item.child(i)
                if setItemVisibility(child, text):
                    child_match = True
            
            # Item is visible if it matches or any child matches
            visible = match or child_match
            item.setHidden(not visible)
            
            return visible
        
        # Apply filter to all top-level items
        for i in range(self.productsTree.topLevelItemCount()):
            item = self.productsTree.topLevelItem(i)
            setItemVisibility(item, text)
    
    def onCloudSelectionChanged(self, item, column):
        """Handle checkbox changes in tree"""
        # Update children
        if item.childCount() > 0:
            checked = item.checkState(0)
            for i in range(item.childCount()):
                child = item.child(i)
                child.setCheckState(0, checked)
                # Recursively update children
                self.onCloudSelectionChanged(child, column)
        
        # Update parent
        parent = item.parent()
        if parent:
            all_checked = all(parent.child(i).checkState(0) == Qt.Checked 
                            for i in range(parent.childCount()))
            any_checked = any(parent.child(i).checkState(0) != Qt.Unchecked 
                            for i in range(parent.childCount()))
            
            if all_checked:
                parent.setCheckState(0, Qt.Checked)
            elif any_checked:
                parent.setCheckState(0, Qt.PartiallyChecked)
            else:
                parent.setCheckState(0, Qt.Unchecked)
        
        self.updateProceedButton()
    
    def browseFiles(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Reference Files",
            "",
            "Data Files (*.eff *.tsf *.zip)"
        )
        if files:
            self.addReferenceFiles(files)
    
    def addReferenceFiles(self, files):
        for file_path in files:
            if file_path not in self.reference_files:
                self.reference_files.append(file_path)
        
        self.updateFileDisplay()
        self.updateProceedButton()
    
    def updateFileDisplay(self):
        """Update the file display to match upload page design"""
        # Clear existing widgets
        while self.filesContainerLayout.count():
            child = self.filesContainerLayout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Add file widgets
        for file_path in self.reference_files:
            fileWidget = FileItemWidget(file_path)
            fileWidget.remove_clicked.connect(self.removeFile)
            self.filesContainerLayout.addWidget(fileWidget)
        
        # Update file count
        self.fileCountLabel.setText(f"({len(self.reference_files)} files)")
    
    def removeFile(self, file_path):
        """Remove a file from the reference files list"""
        if file_path in self.reference_files:
            self.reference_files.remove(file_path)
            self.updateFileDisplay()
            self.updateProceedButton()
    
    def updateProceedButton(self):
        if self.localRadio.isChecked():
            # Enable if reference files are selected
            self.proceedButton.setEnabled(len(self.reference_files) > 0)
        else:
            # Enable if any cloud item is selected
            has_selection = False
            for i in range(self.productsTree.topLevelItemCount()):
                if self.hasCheckedItems(self.productsTree.topLevelItem(i)):
                    has_selection = True
                    break
            self.proceedButton.setEnabled(has_selection)
    
    def hasCheckedItems(self, item):
        """Check if item or any of its children are checked"""
        if item.checkState(0) == Qt.Checked:
            return True
        for i in range(item.childCount()):
            if self.hasCheckedItems(item.child(i)):
                return True
        return False
    
    def getSelectedCloudData(self):
        """Get selected products, lots, and insertions from tree"""
        selected = {
            "products": [],
            "lots": {},
            "insertions": {}
        }
        
        for i in range(self.productsTree.topLevelItemCount()):
            product_item = self.productsTree.topLevelItem(i)
            if product_item.checkState(0) != Qt.Unchecked:
                product_name = product_item.text(0)
                selected["products"].append(product_name)
                selected["lots"][product_name] = []
                selected["insertions"][product_name] = {}
                
                for j in range(product_item.childCount()):
                    lot_item = product_item.child(j)
                    if lot_item.checkState(0) != Qt.Unchecked:
                        lot_name = lot_item.text(0)
                        selected["lots"][product_name].append(lot_name)
                        selected["insertions"][product_name][lot_name] = []
                        
                        for k in range(lot_item.childCount()):
                            insertion_item = lot_item.child(k)
                            if insertion_item.checkState(0) == Qt.Checked:
                                insertion_name = insertion_item.text(0)
                                selected["insertions"][product_name][lot_name].append(insertion_name)
        
        return selected
    
    def set_uploaded_files(self, files):
        """Set the uploaded files from the upload page"""
        self.uploaded_files = files
    
    def go_back(self):
        self.show_upload_signal.emit()
    
    def proceed(self):
        reference_config = {
            "source": "local" if self.localRadio.isChecked() else "cloud",
            "files": self.reference_files if self.localRadio.isChecked() else [],
            "cloud_selection": self.getSelectedCloudData() if self.cloudRadio.isChecked() else {}
        }
        
        # Emit signal with uploaded files and reference configuration
        self.show_selection_signal.emit(self.uploaded_files, reference_config)