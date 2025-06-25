from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLineEdit, QToolButton, QProgressBar,
                             QListWidget, QListWidgetItem)
from PySide6.QtGui import QFont, QIcon, QColor
from PySide6.QtCore import Qt, QSize, Signal, QThread
from ui.utils.PathResources import resource_path
from ui.utils.Effio import EFF
class LoadItemsWorker(QThread):
    finished = Signal(dict)
    
    def __init__(self, files):
        super().__init__()
        self.files = files
    def run(self):
        VAMOS_TEST = {
            "VAMOS_PU": [6000, 6999],
            "VAMOS_CFS": [7000, 7999],
            "VAMOS_IDD": [10000, 19999],
            "VAMOS_PMU": [20000, 29999],
            "VAMOS_GPIO": [30000, 39999],
            "VAMOS_OSC": [40000, 49999],
            "VAMOS_ATPG": [50000, 59999],
            "VAMOS_IDDQ": [60000, 69999],
            "VAMOS_MEM": [70000, 79999],
            "VAMOS_UM": [80000, 89999],
            "VAMOS_LIB": [90000, 99999],
            "VAMOS_spare": [100000, 109999]
        }
        
        file_groups = {}
        for file_path in self.files:
            df, metadata = EFF.read(file_path)
            test_numbers = list(set(EFF.get_test_numbers(df)))
            for key, value in VAMOS_TEST.items():
                tmp = []
                for x in test_numbers:
                    if int(x) in range(value[0], value[1]+1) and x not in tmp:
                        tmp.append(x)
                if tmp:
                    test_names = EFF.get_description_rows(df, header="auto")[tmp].loc['<+ParameterName>'].tolist()
                    file_groups[key] = [f"{x};{y}" for x, y in zip(tmp, test_names)]
        
        self.finished.emit(file_groups)

class GroupListWidget(QListWidget):
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
    show_processing_signal = Signal(list, list)
    
    def __init__(self):
        super().__init__()
        self.files = []
        self.initUI()

    def initUI(self):
        self.setFixedWidth(480)
        self.setMinimumHeight(700)  # Increased height for vertical layout
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
        self.availableList = GroupListWidget()
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
        self.selectedList = GroupListWidget()
        mainLayout.addWidget(selectedLabel)
        mainLayout.addWidget(self.selectedList)
        mainLayout.addWidget(self.loadingWidget)
        mainLayout.setContentsMargins(40,40,40,40)

    def populate_lists(self, file_groups):
        self.availableList.clear()
        
        # Add groups and their items
        for group, items in file_groups.items():
            # Add group header
            group_item = QListWidgetItem(group)
            group_item.setBackground(QColor("#f0f0f0"))
            group_item.setFlags(Qt.ItemIsEnabled)  # Make it non-selectable
            self.availableList.addItem(group_item)
            
            # Add group items
            for item in items:
                test_item = QListWidgetItem(f"  {item}")  # Indent items
                test_item.setData(Qt.UserRole, {"group": group, "item": item})
                self.availableList.addItem(test_item)

    def filter_items(self, text):
        text = text.lower()
        current_group = None
        show_current_group = False

        for i in range(self.availableList.count()):
            item = self.availableList.item(i)
            item_flags = item.flags()
            
            # Check if it's a group header
            if not item_flags & Qt.ItemIsSelectable:
                current_group = item
                show_current_group = False
                item.setHidden(True)  # Hide group initially
            else:
                matches = text in item.text().lower()
                item.setHidden(not matches)
                if matches and current_group:
                    current_group.setHidden(False)

    def move_selected_down(self):
        selected_items = self.availableList.selectedItems()
        for item in selected_items:
            # Only move actual items, not group headers
            if item.flags() & Qt.ItemIsSelectable:
                new_item = QListWidgetItem(item.text())
                new_item.setData(Qt.UserRole, item.data(Qt.UserRole))
                self.selectedList.addItem(new_item)
                self.availableList.takeItem(self.availableList.row(item))
        self.update_process_button_state()

    def move_selected_up(self):
        selected_items = self.selectedList.selectedItems()
        data_to_move = []
        
        # Collect items to move
        for item in selected_items:
            data = item.data(Qt.UserRole)
            data_to_move.append((data["group"], data["item"], item.text()))
            self.selectedList.takeItem(self.selectedList.row(item))
        
        # Find appropriate positions in available list and insert
        for group, item, text in data_to_move:
            # Find group position
            group_index = -1
            for i in range(self.availableList.count()):
                list_item = self.availableList.item(i)
                if not list_item.flags() & Qt.ItemIsSelectable and list_item.text() == group:
                    group_index = i
                    break
            
            if group_index != -1:
                # Find position after group header
                insert_pos = group_index + 1
                while (insert_pos < self.availableList.count() and 
                       self.availableList.item(insert_pos).flags() & Qt.ItemIsSelectable):
                    insert_pos += 1
                
                new_item = QListWidgetItem(text)
                new_item.setData(Qt.UserRole, {"group": group, "item": item})
                self.availableList.insertItem(insert_pos, new_item)
        
        self.update_process_button_state()

    def move_all_down(self):
        i = 0
        while i < self.availableList.count():
            item = self.availableList.item(i)
            if item.flags() & Qt.ItemIsSelectable:  # Only move selectable items
                new_item = QListWidgetItem(item.text())
                new_item.setData(Qt.UserRole, item.data(Qt.UserRole))
                self.selectedList.addItem(new_item)
                self.availableList.takeItem(i)
            else:
                i += 1
        self.update_process_button_state()

    def move_all_up(self):
        if self.selectedList.count() == 0:
            return

        items_to_move = []
        for i in range(self.selectedList.count()):
            item = self.selectedList.item(i)
            data = item.data(Qt.UserRole)
            items_to_move.append((data["group"], data["item"], item.text()))
        
        self.selectedList.clear()
        items_to_move.sort(key=lambda x: x[0])
        group_positions = {}
        for i in range(self.availableList.count()):
            item = self.availableList.item(i)
            if not item.flags() & Qt.ItemIsSelectable: 
                group_positions[item.text()] = i
        
        current_group = None
        for group, item, text in items_to_move:
            if group != current_group:
                if group not in group_positions:
                    group_item = QListWidgetItem(group)
                    group_item.setBackground(QColor("#f0f0f0"))
                    group_item.setFlags(Qt.ItemIsEnabled)
                    self.availableList.addItem(group_item)
                    group_positions[group] = self.availableList.count() - 1
                current_group = group
            
            insert_pos = group_positions[group] + 1
            while (insert_pos < self.availableList.count() and 
                self.availableList.item(insert_pos).flags() & Qt.ItemIsSelectable and
                self.availableList.item(insert_pos).data(Qt.UserRole)["group"] == group):
                insert_pos += 1
            
            new_item = QListWidgetItem(text)
            new_item.setData(Qt.UserRole, {"group": group, "item": item})
            self.availableList.insertItem(insert_pos, new_item)
            
            for g, pos in group_positions.items():
                if pos >= insert_pos:
                    group_positions[g] += 1

    def update_process_button_state(self):
        has_selection = self.selectedList.count() > 0
        self.processButton.setEnabled(has_selection)

    def get_selected_items(self):
        selected_items = []
        for i in range(self.selectedList.count()):
            item = self.selectedList.item(i)
            data = item.data(Qt.UserRole)
            if data:  # Only add actual test items, not group headers
                selected_items.append(f"{data['item']}")
        return selected_items

    def process_selected(self):
        selected_items = self.get_selected_items()
        if selected_items:
            self.show_processing_signal.emit(selected_items, self.files)

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

    def on_loading_finished(self, file_groups):
        self.loadingWidget.hide()
        self.populate_lists(file_groups)
    
    def set_reference_config(self, reference_config):
        """Store reference configuration for processing"""
        self.reference_config = reference_config