from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QRadioButton, 
                               QButtonGroup, QFileDialog, QMessageBox,
                               QLineEdit, QListWidget, QListWidgetItem,
                               QScrollArea, QTreeWidget, QTreeWidgetItem,
                               QFrame, QCheckBox, QGroupBox, QProgressBar,
                               QToolButton)
from PySide6.QtCore import Qt, Signal, QMimeData, QSize, QThread
from PySide6.QtGui import QFont, QPixmap, QDragEnterEvent, QDropEvent, QPainter, QBrush, QColor, QIcon
import os
from pathlib import Path
from api.settings_client import SettingsClient
from api.reference_data_client import ReferenceDataClient
from ui.utils.PathResources import resource_path

class LoadCloudDataWorker(QThread):
    """Worker thread for loading cloud data"""
    finished = Signal(dict)
    error = Signal(str)
    
    def __init__(self, reference_client):
        super().__init__()
        self.reference_client = reference_client
    
    def run(self):
        try:
            data = self.reference_client.get_reference_data_structure()
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))

class DragDropArea(QFrame):
    """Custom drag and drop area widget matching upload page style"""
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
        uploadIcon.setStyleSheet("border: none;")
        
        # Upload text
        uploadText = QLabel('Drag your reference file(s) or <span style="color:#1849D6;">browse</span>')
        uploadText.setAlignment(Qt.AlignCenter)
        uploadText.setStyleSheet("color: #666666; border: none;")
        
        layout.addStretch()
        layout.addWidget(uploadIcon, alignment=Qt.AlignCenter)
        layout.addWidget(uploadText, alignment=Qt.AlignCenter)
        layout.addStretch()
        
        # Make the entire area clickable
        self.mousePressEvent = self.on_click
    
    def on_click(self, event):
        """Handle click to browse files"""
        self.browse_files()
    
    def browse_files(self):
        """Open file dialog"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Reference Files",
            "",
            "Data Files (*.eff *.tsf *.zip)"
        )
        if files:
            self.files_dropped.emit(files)
    
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
        try:
            icon_path = self.get_icon_path(self.file_path)
            iconPixmap = QPixmap(icon_path)
            iconPixmap = iconPixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            iconLabel.setPixmap(iconPixmap)
        except:
            # Fallback: create a simple colored rectangle as file icon
            iconPixmap = QPixmap(40, 40)
            iconPixmap.fill(QColor("#1849D6"))
            iconLabel.setPixmap(iconPixmap)
        
        iconLabel.setStyleSheet("border: none;")
        
        # File info layout
        infoLayout = QVBoxLayout()
        infoLayout.setSpacing(2)
        
        # File name
        fileName = QLabel(os.path.basename(self.file_path))
        fileName.setStyleSheet("font-weight: bold; color: #333333; border: none;")
        
        # File size
        try:
            file_size = os.path.getsize(self.file_path) / (1024 * 1024)  # Convert to MB
            sizeLabel = QLabel(f"{file_size:.2f} MB")
        except:
            sizeLabel = QLabel("Unknown size")
        sizeLabel.setStyleSheet("color: #666666; font-size: 10px; border: none;")
        
        infoLayout.addWidget(fileName)
        infoLayout.addWidget(sizeLabel)
        
        # Remove button
        removeBtn = QPushButton()
        removeBtn.setIcon(QPixmap(resource_path('./resources/icons/delete.png')).scaled(
            20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        removeBtn.setFixedSize(25, 25)
        removeBtn.setStyleSheet("""
            QPushButton {
                border: none;
            }
        """)
        removeBtn.clicked.connect(lambda: self.remove_clicked.emit(self.file_path))
        
        layout.addWidget(iconLabel)
        layout.addLayout(infoLayout)
        layout.addStretch()
        layout.addWidget(removeBtn)
        
        # Container styling matching upload page
        self.setStyleSheet("""
            FileItemWidget {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                max-height: 60px;
                margin: 2px;
            }
        """)
    
    def get_icon_path(self, filePath):
        """Get appropriate icon for file type"""
        if filePath.endswith('.zip'):
            return resource_path('./resources/icons/ZIP.png')
        elif filePath.endswith('.eff'):
            return resource_path('./resources/icons/EFF.png')
        elif filePath.endswith('.tsf'):
            return resource_path('./resources/icons/TSF.png')
        return resource_path('./resources/icons/default.png')

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
        self.cloud_worker = None
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
        
        # Apply checkbox styling to radio buttons
        radio_style = """
            QRadioButton {
                border: none;
                margin-bottom: 10px;
            }
            QRadioButton::indicator {
                width: 15px;
                height: 15px;
                border: 1px solid #DADEE8;
                border-radius: 7px;
                background-color: white;
            }
            QRadioButton::indicator:checked {
                background-color: #1849D6;
                border: 1px solid #1849D6;
            }
            QRadioButton::indicator:checked::after {
                content: '';
                width: 6px;
                height: 6px;
                border-radius: 3px;
                background-color: white;
                position: absolute;
                top: 4px;
                left: 4px;
            }
        """
        
        self.localRadio.setStyleSheet(radio_style)
        self.cloudRadio.setStyleSheet(radio_style)
        
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
        # Drag and drop area matching upload page
        self.dragDropArea = DragDropArea()
        self.dragDropArea.files_dropped.connect(self.addReferenceFiles)
        self.contentLayout.addWidget(self.dragDropArea)
        
        # Support message matching upload page
        message = QLabel("Only support .eff, .tsf, and .zip files")
        message.setStyleSheet("color: gray; margin-top: 0px; margin-bottom: 10px;")
        self.contentLayout.addWidget(message)
        
        # Clear All button matching upload page
        self.clearFilesButton = QPushButton("Clear All")
        self.clearFilesButton.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #FF0000;
                border: 1px solid #FF0000;
                border-radius: 5px;
                padding: 5px 15px;
                margin-bottom: 10px;
            }
        """)
        self.clearFilesButton.clicked.connect(self.clearAllFiles)
        self.contentLayout.addWidget(self.clearFilesButton)
        
        # Files container
        self.fileListScrollArea = QScrollArea()
        self.fileListScrollArea.setMinimumHeight(200)
        self.fileListScrollArea.setWidgetResizable(True)
        self.fileListScrollArea.setStyleSheet("QScrollArea { border: none; }")
        
        self.fileListContent = QWidget()
        self.fileListLayout = QVBoxLayout(self.fileListContent)
        self.fileListLayout.setAlignment(Qt.AlignTop)
        self.fileListScrollArea.setWidget(self.fileListContent)
        
        self.contentLayout.addWidget(self.fileListScrollArea)
        
        # Update display
        self.updateFileDisplay()
        self.updateProceedButton()
    
    def showCloudSelectionInterface(self):
        # Search bar matching SelectionPage style
        searchContainer = QWidget()
        searchContainer.setStyleSheet("""
            background-color: rgba(24, 73, 214, 0.08);
            border-radius: 19px;
        """)
        searchContainerLayout = QHBoxLayout(searchContainer)
        searchContainerLayout.setContentsMargins(15, 3, 3, 3)
        
        self.searchInput = QLineEdit()
        self.searchInput.setPlaceholderText("Search products, insertions, or lots...")
        self.searchInput.setStyleSheet("background-color: transparent; border: none;")
        self.searchInput.setFixedHeight(30)
        self.searchInput.textChanged.connect(self.filterCloudData)
        
        searchIcon = QToolButton()
        searchIcon.setIcon(QIcon(resource_path("./resources/icons/search.png")))
        searchIcon.setIconSize(QSize(30, 30))
        searchIcon.setStyleSheet("background: transparent; border: none;")
        
        searchContainerLayout.addWidget(self.searchInput)
        searchContainerLayout.addWidget(searchIcon)
        self.contentLayout.addWidget(searchContainer)
        
        # Loading indicator
        self.loadingWidget = QWidget()
        loadingLayout = QVBoxLayout(self.loadingWidget)
        loadingLabel = QLabel("Loading reference data...")
        loadingLabel.setAlignment(Qt.AlignCenter)
        loadingLabel.setStyleSheet("color: #666666; margin: 20px;")
        
        self.loadingProgress = QProgressBar()
        self.loadingProgress.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #1849D6;
                width: 10px;
            }
        """)
        self.loadingProgress.setMinimum(0)
        self.loadingProgress.setMaximum(0) 
        
        loadingLayout.addWidget(loadingLabel)
        loadingLayout.addWidget(self.loadingProgress)
        loadingLayout.setContentsMargins(20, 40, 20, 40)
        self.contentLayout.addWidget(self.loadingWidget)
        
        # Products tree (initially hidden)
        productsLabel = QLabel("Available Products:")
        productsLabel.setFont(QFont("Arial", 10, QFont.Bold))
        productsLabel.setStyleSheet("margin-top: 10px; background-color: transparent;")
        productsLabel.hide()
        self.productsLabelWidget = productsLabel
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
                background-color: white;
                color: black;
            }
            QTreeWidget::indicator {
                width: 15px;
                height: 15px;
                border: 1px solid #DADEE8;
                border-radius: 5px;
                background-color: white;
            }
            QTreeWidget::indicator:checked {
                background-color: #1849D6;
                border: 1px solid #1849D6;
            }
        """)
        self.productsTree.itemChanged.connect(self.onCloudSelectionChanged)
        self.productsTree.hide()
        
        scrollArea = QScrollArea()
        scrollArea.setWidget(self.productsTree)
        scrollArea.setWidgetResizable(True)
        scrollArea.setMaximumHeight(400)
        scrollArea.hide()
        self.productsScrollArea = scrollArea
        self.contentLayout.addWidget(scrollArea)
        
        # Load cloud data
        self.loadCloudData()
    
    def loadCloudData(self):
        """Load available products from cloud"""
        if self.cloud_worker and self.cloud_worker.isRunning():
            return
        
        self.cloud_worker = LoadCloudDataWorker(self.reference_client)
        self.cloud_worker.finished.connect(self.onCloudDataLoaded)
        self.cloud_worker.error.connect(self.onCloudDataError)
        self.cloud_worker.start()
    
    def onCloudDataLoaded(self, data):
        """Handle successful cloud data loading"""
        self.loadingWidget.hide()
        self.productsLabelWidget.show()
        self.productsTree.show()
        self.productsScrollArea.show()
        
        self.populateCloudTree(data)
    
    def onCloudDataError(self, error_message):
        """Handle cloud data loading error"""
        self.loadingWidget.hide()
        
        # Show error message
        errorLabel = QLabel(f"Error loading reference data: {error_message}")
        errorLabel.setStyleSheet("color: red; margin: 20px;")
        errorLabel.setWordWrap(True)
        self.contentLayout.addWidget(errorLabel)
        
        QMessageBox.critical(
            self, 
            "Connection Error", 
            f"Failed to load reference data from cloud:\n{error_message}\n\nPlease check your connection or use local reference data."
        )
    
    def populateCloudTree(self, data):
        """Populate tree with cloud data in Product > Insertion > Lot order"""
        self.productsTree.clear()
        
        products = data.get("products", {})
        
        if not products:
            noDataItem = QTreeWidgetItem(self.productsTree, ["No reference data available in cloud"])
            self.productsTree.addTopLevelItem(noDataItem)
            QMessageBox.information(self, "No Data", "No reference data is currently available in the cloud. Please upload reference data locally or contact your administrator.")
            return
        
        # Reorganize data: Product > Insertion > Lot
        for product, product_data in products.items():
            productItem = QTreeWidgetItem(self.productsTree, [product])
            productItem.setFlags(productItem.flags() | Qt.ItemIsUserCheckable)
            productItem.setCheckState(0, Qt.Unchecked)
            
            # Collect all insertions for this product
            insertions_data = {}
            lots = product_data.get("lots", {})
            for lot, insertions in lots.items():
                for insertion in insertions:
                    if insertion not in insertions_data:
                        insertions_data[insertion] = []
                    insertions_data[insertion].append(lot)
            
            # Create tree structure: Product > Insertion > Lot
            for insertion, lots_for_insertion in insertions_data.items():
                insertionItem = QTreeWidgetItem(productItem, [insertion])
                insertionItem.setFlags(insertionItem.flags() | Qt.ItemIsUserCheckable)
                insertionItem.setCheckState(0, Qt.Unchecked)
                
                for lot in lots_for_insertion:
                    lotItem = QTreeWidgetItem(insertionItem, [lot])
                    lotItem.setFlags(lotItem.flags() | Qt.ItemIsUserCheckable)
                    lotItem.setCheckState(0, Qt.Unchecked)
        
        self.productsTree.expandAll()
    
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
    
    def addReferenceFiles(self, files):
        for file_path in files:
            if file_path not in self.reference_files:
                self.reference_files.append(file_path)
        
        self.updateFileDisplay()
        self.updateProceedButton()
    
    def updateFileDisplay(self):
        """Update the file display to match upload page design"""
        # Clear existing widgets
        while self.fileListLayout.count():
            child = self.fileListLayout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Add file widgets
        for file_path in self.reference_files:
            fileWidget = FileItemWidget(file_path)
            fileWidget.remove_clicked.connect(self.removeFile)
            self.fileListLayout.addWidget(fileWidget)
    
    def removeFile(self, file_path):
        """Remove a file from the reference files list"""
        if file_path in self.reference_files:
            self.reference_files.remove(file_path)
            self.updateFileDisplay()
            self.updateProceedButton()
    
    def clearAllFiles(self):
        """Clear all reference files"""
        self.reference_files.clear()
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
        """Get selected products, insertions, and lots from tree"""
        selected = {
            "products": [],
            "insertions": {},
            "lots": {}
        }
        
        for i in range(self.productsTree.topLevelItemCount()):
            product_item = self.productsTree.topLevelItem(i)
            if product_item.checkState(0) != Qt.Unchecked:
                product_name = product_item.text(0)
                selected["products"].append(product_name)
                selected["insertions"][product_name] = []
                selected["lots"][product_name] = {}
                
                for j in range(product_item.childCount()):
                    insertion_item = product_item.child(j)
                    if insertion_item.checkState(0) != Qt.Unchecked:
                        insertion_name = insertion_item.text(0)
                        selected["insertions"][product_name].append(insertion_name)
                        selected["lots"][product_name][insertion_name] = []
                        
                        for k in range(insertion_item.childCount()):
                            lot_item = insertion_item.child(k)
                            if lot_item.checkState(0) == Qt.Checked:
                                lot_name = lot_item.text(0)
                                selected["lots"][product_name][insertion_name].append(lot_name)
        
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