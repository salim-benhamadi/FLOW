from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLineEdit, QToolButton, QProgressBar,
                             QListWidget, QListWidgetItem)
from PySide6.QtGui import QFont, QIcon, QColor
from PySide6.QtCore import Qt, QSize, Signal, QThread
from ui.utils.PathResources import resource_path
from ui.utils.Effio import EFF

class LoadItemsWorker(QThread):
    finished = Signal(list)  # Changed from dict to list since we're not grouping
    
    def __init__(self, files):
        super().__init__()
        self.files = files
        
    def run(self):
        all_tests = []
        for file_path in self.files:
            df, metadata = EFF.read(file_path)
            test_numbers = list(set(EFF.get_test_numbers(df)))
            
            # Get test names for all test numbers
            if test_numbers:
                test_names = EFF.get_description_rows(df, header="auto")[test_numbers].loc['<+ParameterName>'].tolist()
                # Create test items with format "test_number;test_name"
                for test_num, test_name in zip(test_numbers, test_names):
                    test_item = f"{test_num};{test_name}"
                    if test_item not in all_tests:  # Avoid duplicates
                        all_tests.append(test_item)
        
        # Sort tests by test number
        all_tests.sort(key=lambda x: int(x.split(';')[0]))
        self.finished.emit(all_tests)

class TestListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QListWidget.ExtendedSelection)  
        self.setStyleSheet("""
            QListWidget {
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                background-color: white;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #1849D6;
                color: white;
            }
        """)

class SelectionPage(QWidget):
    show_upload_signal = Signal()
    show_processing_signal = Signal(list, list, dict)  # Added reference_config parameter
    
    def __init__(self):
        super().__init__()
        self.files = []
        self.reference_config = {}  # Store reference configuration
        self.initUI()

    def initUI(self):
        self.setFixedWidth(530)
        self.setMinimumHeight(700)
        self.setStyleSheet("background-color: white; color: black")
        
        mainLayout = QVBoxLayout(self)
        mainLayout.setSpacing(10)
        
        # Header section
        headerLayout = QHBoxLayout()
        titleLayout = QVBoxLayout()
        title = QLabel("Select Tests")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        subtitle = QLabel("Choose the test that you want to analyze")
        subtitle.setFont(QFont("Arial", 8))
        subtitle.setStyleSheet("color: gray;")
        
        titleLayout.addWidget(title)
        titleLayout.addWidget(subtitle)
        headerLayout.addLayout(titleLayout)
        
        # Action buttons
        buttonLayout = QHBoxLayout()
        self.backButton = QPushButton("Back")
        self.backButton.setStyleSheet("""
            QPushButton {
                background-color: #FFA500;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
                margin-right: 10px;
            }
        """)
        self.backButton.clicked.connect(self.go_back)
        
        self.processButton = QPushButton("Process")
        self.processButton.setEnabled(False)
        self.processButton.setStyleSheet("""
            QPushButton {
                background-color: #CCCCCC;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
            }
            QPushButton:enabled {
                background-color: #1849D6;
            }
        """)
        self.processButton.clicked.connect(self.process_selected)
        
        buttonLayout.addWidget(self.backButton)
        buttonLayout.addWidget(self.processButton)
        headerLayout.addStretch()
        headerLayout.addLayout(buttonLayout)
        headerLayout.setContentsMargins(0,0,0,20)
        mainLayout.addLayout(headerLayout)

        # Search bar
        searchLayout = QHBoxLayout()
        searchContainer = QWidget()
        searchContainer.setStyleSheet("""
            background-color: rgba(24, 73, 214, 0.08);
            border-radius: 19px;
        """)
        searchContainerLayout = QHBoxLayout(searchContainer)
        searchContainerLayout.setContentsMargins(15,3,3,3)
        
        self.searchBox = QLineEdit()
        self.searchBox.setPlaceholderText("Search...")
        self.searchBox.setStyleSheet("background-color: transparent;")
        self.searchBox.setFixedHeight(30)
        self.searchBox.textChanged.connect(self.filter_items)
        
        searchIcon = QToolButton()
        searchIcon.setIcon(QIcon(resource_path("./resources/icons/search.png")))
        searchIcon.setIconSize(QSize(30, 30))
        searchIcon.setStyleSheet("background: transparent; border: none;")
        
        searchContainerLayout.addWidget(self.searchBox)
        searchContainerLayout.addWidget(searchIcon)
        searchLayout.addWidget(searchContainer)
        mainLayout.addLayout(searchLayout)

        # Loading indicator
        self.loadingWidget = QWidget()
        loadingLayout = QVBoxLayout(self.loadingWidget)
        self.progressBar = QProgressBar()
        self.progressBar.setStyleSheet("""
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
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(0)
        loadingLayout.addWidget(self.progressBar)
        self.loadingWidget.hide()
        
        # Available list section
        availableLabel = QLabel("Available Tests")
        availableLabel.setFont(QFont("Arial", 10, QFont.Bold))
        self.availableList = TestListWidget()
        mainLayout.addWidget(availableLabel)
        mainLayout.addWidget(self.availableList)

        # Transfer buttons
        transferLayout = QHBoxLayout()
        
        self.moveDownButton = QPushButton("↓")
        self.moveUpButton = QPushButton("↑")
        self.moveAllDownButton = QPushButton("Move All ↓")
        self.moveAllUpButton = QPushButton("Remove All ↑")
        
        transfer_button_style = """
            QPushButton {
                background-color: #1849D6;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
                margin: 5px;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """
        
        for button in [self.moveDownButton, self.moveUpButton, 
                      self.moveAllDownButton, self.moveAllUpButton]:
            button.setStyleSheet(transfer_button_style)
            
        self.moveDownButton.clicked.connect(self.move_selected_down)
        self.moveUpButton.clicked.connect(self.move_selected_up)
        self.moveAllDownButton.clicked.connect(self.move_all_down)
        self.moveAllUpButton.clicked.connect(self.move_all_up)
        
        transferLayout.addWidget(self.moveDownButton)
        transferLayout.addWidget(self.moveUpButton)
        transferLayout.addWidget(self.moveAllDownButton)
        transferLayout.addWidget(self.moveAllUpButton)
        mainLayout.addLayout(transferLayout)

        # Selected list section
        selectedLabel = QLabel("Selected Tests")
        selectedLabel.setFont(QFont("Arial", 10, QFont.Bold))
        self.selectedList = TestListWidget()
        mainLayout.addWidget(selectedLabel)
        mainLayout.addWidget(self.selectedList)
        mainLayout.addWidget(self.loadingWidget)
        mainLayout.setContentsMargins(40,40,40,40)

    def populate_lists(self, all_tests):
        self.availableList.clear()
        
        # Add all tests directly without grouping
        for test_item in all_tests:
            list_item = QListWidgetItem(test_item)
            list_item.setData(Qt.UserRole, {"item": test_item})
            self.availableList.addItem(list_item)

    def filter_items(self, text):
        text = text.lower()
        
        for i in range(self.availableList.count()):
            item = self.availableList.item(i)
            matches = text in item.text().lower()
            item.setHidden(not matches)

    def move_selected_down(self):
        selected_items = self.availableList.selectedItems()
        for item in selected_items:
            new_item = QListWidgetItem(item.text())
            new_item.setData(Qt.UserRole, item.data(Qt.UserRole))
            self.selectedList.addItem(new_item)
            self.availableList.takeItem(self.availableList.row(item))
        self.update_process_button_state()

    def move_selected_up(self):
        selected_items = self.selectedList.selectedItems()
        items_to_move = []
        
        # Collect items to move
        for item in selected_items:
            data = item.data(Qt.UserRole)
            items_to_move.append((data["item"], item.text()))
            self.selectedList.takeItem(self.selectedList.row(item))
        
        # Sort items by test number to maintain order
        items_to_move.sort(key=lambda x: int(x[0].split(';')[0]))
        
        # Add items back to available list in sorted order
        for item_data, text in items_to_move:
            # Find correct position to insert (maintain sorted order)
            insert_pos = 0
            for i in range(self.availableList.count()):
                existing_item = self.availableList.item(i)
                existing_test_num = int(existing_item.data(Qt.UserRole)["item"].split(';')[0])
                current_test_num = int(item_data.split(';')[0])
                if current_test_num < existing_test_num:
                    insert_pos = i
                    break
                insert_pos = i + 1
            
            new_item = QListWidgetItem(text)
            new_item.setData(Qt.UserRole, {"item": item_data})
            self.availableList.insertItem(insert_pos, new_item)
        
        self.update_process_button_state()

    def move_all_down(self):
        # Move all items from available to selected
        items_to_move = []
        for i in range(self.availableList.count()):
            item = self.availableList.item(i)
            items_to_move.append((item.text(), item.data(Qt.UserRole)))
        
        self.availableList.clear()
        
        for text, data in items_to_move:
            new_item = QListWidgetItem(text)
            new_item.setData(Qt.UserRole, data)
            self.selectedList.addItem(new_item)
        
        self.update_process_button_state()

    def move_all_up(self):
        if self.selectedList.count() == 0:
            return

        # Move all items from selected back to available
        items_to_move = []
        for i in range(self.selectedList.count()):
            item = self.selectedList.item(i)
            data = item.data(Qt.UserRole)
            items_to_move.append((data["item"], item.text()))
        
        self.selectedList.clear()
        
        # Sort by test number
        items_to_move.sort(key=lambda x: int(x[0].split(';')[0]))
        
        # Add back to available list in sorted order
        for item_data, text in items_to_move:
            # Find correct position to insert
            insert_pos = 0
            for i in range(self.availableList.count()):
                existing_item = self.availableList.item(i)
                existing_test_num = int(existing_item.data(Qt.UserRole)["item"].split(';')[0])
                current_test_num = int(item_data.split(';')[0])
                if current_test_num < existing_test_num:
                    insert_pos = i
                    break
                insert_pos = i + 1
            
            new_item = QListWidgetItem(text)
            new_item.setData(Qt.UserRole, {"item": item_data})
            self.availableList.insertItem(insert_pos, new_item)
        
        self.update_process_button_state()

    def update_process_button_state(self):
        has_selection = self.selectedList.count() > 0
        self.processButton.setEnabled(has_selection)

    def get_selected_items(self):
        selected_items = []
        for i in range(self.selectedList.count()):
            item = self.selectedList.item(i)
            data = item.data(Qt.UserRole)
            if data:  # Only add actual test items
                selected_items.append(f"{data['item']}")
        return selected_items

    def process_selected(self):
        selected_items = self.get_selected_items()
        if selected_items:
            # Pass reference configuration along with selected items and files
            self.show_processing_signal.emit(selected_items, self.files, self.reference_config)

    def go_back(self):
        self.show_upload_signal.emit()

    def set_files(self, file_paths: list):
        self.files = file_paths
        self.availableList.clear()
        self.selectedList.clear()
        self.loadingWidget.show()
        
        self.worker = LoadItemsWorker(self.files)
        self.worker.finished.connect(self.on_loading_finished)
        self.worker.start()

    def on_loading_finished(self, all_tests):
        self.loadingWidget.hide()
        self.populate_lists(all_tests)
    
    def set_reference_config(self, reference_config):
        """Store reference configuration for processing"""
        self.reference_config = reference_config