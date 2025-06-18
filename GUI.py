import os
import sys
import json
import csv
import subprocess
import shutil
import tempfile
import UnityPy
import re
import urllib.request
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QScrollArea, QHBoxLayout, QLabel, QLineEdit,
    QFileDialog, QMessageBox, QProgressDialog, QTableWidget,
    QTableWidgetItem, QHeaderView
)
from PyQt6.QtGui import QIcon, QColor, QPalette
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer

def download_file(url, destination):
    """Downloads a file from a URL to a destination path."""
    try:
        urllib.request.urlretrieve(url, destination)
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

class AssetExtractor(QThread):
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(str, str, str)

    def __init__(self, bundle_path, spine_assets_dir):
        super().__init__()
        self.bundle_path = bundle_path
        self.spine_assets_dir = spine_assets_dir
        self.cancelled = False

    def run(self):
        try:
            bundle_name = os.path.splitext(os.path.basename(self.bundle_path))[0]
            output_dir = os.path.join(self.spine_assets_dir, bundle_name)

            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
            os.makedirs(output_dir, exist_ok=True)

            self.progress_signal.emit(10, "Loading bundle...")
            env = UnityPy.load(self.bundle_path)
            self.progress_signal.emit(20, "Scanning assets...")

            spine_assets = {'skel': None, 'atlas': None, 'textures': []}
            objects = list(env.objects)
            for i, obj in enumerate(objects):
                if self.cancelled:
                    break
                progress = 20 + int((i / len(objects)) * 70)
                self.progress_signal.emit(progress, f"Processing {obj.type.name}...")

                try:
                    data = obj.read()

                    if obj.type.name == "Texture2D":
                        texture_name = f"{data.m_Name}.png"
                        texture_path = os.path.join(output_dir, texture_name)
                        data.image.save(texture_path)
                        spine_assets['textures'].append(texture_path)

                    elif obj.type.name == "TextAsset":
                        asset_name = data.m_Name
                        asset_path = os.path.join(output_dir, asset_name)

                        if asset_name.endswith('.skel') or '.skel.' in asset_name:
                            spine_assets['skel'] = asset_path
                        elif asset_name.endswith('.atlas') or '.atlas.' in asset_name:
                            spine_assets['atlas'] = asset_path

                        with open(asset_path, "wb") as f:
                            f.write(data.m_Script.encode("utf-8", "surrogateescape"))

                except Exception as e:
                    print(f"Error processing asset: {e}")

            if self.cancelled:
                shutil.rmtree(output_dir)
                self.finished_signal.emit(None, None, "Extraction cancelled")
            else:
                self.progress_signal.emit(95, "Finalizing...")
                if spine_assets['skel']:
                    self.finished_signal.emit(
                        output_dir,
                        spine_assets['skel'],
                        "Extraction complete"
                    )
                else:
                    self.finished_signal.emit(
                        output_dir,
                        None,
                        "No Spine skeleton file found"
                    )
                self.progress_signal.emit(100, "Done")

        except Exception as e:
            self.finished_signal.emit(None, None, f"Extraction failed: {str(e)}")

    def cancel(self):
        self.cancelled = True

class SpineViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.settings_file = "spine_viewer_settings.json"
        self.naps_settings_file = "naps_settings.json"
        self.setWindowTitle("NIKKE Lobby/Burst Mod Manager")
        self.setGeometry(100, 100, 1200, 800)
        self.viewer_processes = []
        self.character_data = []
        self.character_url_data = []

        # Run automatic updaters first
        self.check_json_updates()
        self.check_csv_updates()
        
        # Load data and settings
        self.character_map = self.load_character_map()
        self.settings = self.load_settings()
        self.naps_settings = self.load_naps_settings()
        self.load_character_data()
        self.load_character_url_data()

        self.set_windows11_dark_theme()

        main_layout = QVBoxLayout()

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Mods Folder:"))
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Path to your mods folder")
        if self.settings.get("mods_folder"):
            self.folder_edit.setText(self.settings["mods_folder"])
        folder_layout.addWidget(self.folder_edit)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_mods_folder)
        folder_layout.addWidget(browse_btn)
        refresh_btn = QPushButton("Refresh Mods List")
        refresh_btn.clicked.connect(self.load_mods)
        folder_layout.addWidget(refresh_btn)
        main_layout.addLayout(folder_layout)

        naps_layout = QHBoxLayout()
        naps_layout.addWidget(QLabel("naps Folder:"))
        self.naps_edit = QLineEdit()
        self.naps_edit.setPlaceholderText("Path to your naps folder")
        if self.naps_settings.get("naps_folder"):
            self.naps_edit.setText(self.naps_settings["naps_folder"])
        naps_layout.addWidget(self.naps_edit)
        naps_browse_btn = QPushButton("Browse...")
        naps_browse_btn.clicked.connect(self.browse_naps_folder)
        naps_layout.addWidget(naps_browse_btn)
        main_layout.addLayout(naps_layout)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filter mods...")
        self.search_edit.textChanged.connect(self.filter_mods)
        search_layout.addWidget(self.search_edit)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(clear_btn)
        main_layout.addLayout(search_layout)

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(8)
        self.table_widget.setHorizontalHeaderLabels(["Author", "ID", "Character", "Skin", "Mod Name", "Type", "Status", "Actions"])
        
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)

        self.table_widget.verticalHeader().setVisible(False)
        self.table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_widget.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table_widget.verticalHeader().setMinimumSectionSize(40)
        
        main_layout.addWidget(self.table_widget)
        self.setLayout(main_layout)

        self.current_extraction = None
        self.progress_dialog = None

        self.verify_mods_folder()
        self.folder_edit.textChanged.connect(self.folder_path_changed)
        self.naps_edit.textChanged.connect(self.naps_path_changed)

    def load_character_data(self):
        self.character_data = []
        
        files_to_load = [
            os.path.join("AddressablesJSON", "lobby_burst_merged_data.json"),
            os.path.join("AddressablesJSON", "lobby_event_data.json")
        ]
        
        for file_path in files_to_load:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.character_data.extend(json.load(f))
            except FileNotFoundError:
                print(f"Data file not found: {file_path}")
            except Exception as e:
                print(f"Error loading character data from {file_path}: {e}")

    def load_character_url_data(self):
        self.character_url_data = []
        
        files_to_load = [
            os.path.join("AddressablesJSON", "lobby_burst_merged_data_URL.json"),
            os.path.join("AddressablesJSON", "lobby_event_data_URL.json")
        ]

        for file_path in files_to_load:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.character_url_data.extend(json.load(f))
            except FileNotFoundError:
                print(f"URL data file not found: {file_path}")
            except Exception as e:
                print(f"Error loading character URL data from {file_path}: {e}")

    def check_json_updates(self):
        """Checks for updates to JSON data files from GitHub and overwrites them if different."""
        files_to_check = {
            "lobby_burst_merged_data.json": "https://raw.githubusercontent.com/kxdekxde/nikke-lobbyburst-mod-manager/refs/heads/main/AddressablesJSON/lobby_burst_merged_data.json",
            "lobby_burst_merged_data_URL.json": "https://raw.githubusercontent.com/kxdekxde/nikke-lobbyburst-mod-manager/refs/heads/main/AddressablesJSON/lobby_burst_merged_data_URL.json",
            "lobby_event_data.json": "https://raw.githubusercontent.com/kxdekxde/nikke-lobbyburst-mod-manager/refs/heads/main/AddressablesJSON/lobby_event_data.json",
            "lobby_event_data_URL.json": "https://raw.githubusercontent.com/kxdekxde/nikke-lobbyburst-mod-manager/refs/heads/main/AddressablesJSON/lobby_event_data_URL.json"
        }

        local_dir = "AddressablesJSON"
        os.makedirs(local_dir, exist_ok=True)

        for filename, url in files_to_check.items():
            local_path = os.path.join(local_dir, filename)
            temp_path = os.path.join(tempfile.gettempdir(), f"temp_{filename}")

            try:
                print(f"Checking for updates for {filename}...")
                if not download_file(url, temp_path):
                    print(f"Failed to download {filename}. Skipping update check.")
                    continue

                update_required = not os.path.exists(local_path)

                if not update_required:
                    # Compare file content to see if an update is needed
                    try:
                        with open(local_path, 'r', encoding='utf-8') as f_local, \
                             open(temp_path, 'r', encoding='utf-8') as f_temp:
                            if json.load(f_local) != json.load(f_temp):
                                update_required = True
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # Fallback to text comparison if JSON parsing fails
                        with open(local_path, 'r', encoding='utf-8', errors='ignore') as f_local, \
                             open(temp_path, 'r', encoding='utf-8', errors='ignore') as f_temp:
                            if f_local.read() != f_temp.read():
                                update_required = True
                
                if update_required:
                    shutil.copy(temp_path, local_path)
                    print(f"Updated {filename} from GitHub.")
                else:
                    print(f"{filename} is already up to date.")

            except Exception as e:
                print(f"Error while checking/updating {filename}: {e}")
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

    def check_csv_updates(self):
        csv_files_to_check = {
            "Codes_and_Names.csv": "https://raw.githubusercontent.com/kxdekxde/nikke-lobbyburst-mod-manager/refs/heads/main/Codes_and_Names.csv",
            "Codes_and_Names_EventLobby.csv": "https://raw.githubusercontent.com/kxdekxde/nikke-lobbyburst-mod-manager/refs/heads/main/Codes_and_Names_EventLobby.csv"
        }
        
        for local_path, github_url in csv_files_to_check.items():
            try:
                temp_path = os.path.join(tempfile.gettempdir(), f"temp_{os.path.basename(local_path)}")
                if download_file(github_url, temp_path):
                    update_required = False
                    if os.path.exists(local_path):
                        with open(local_path, 'r', encoding='utf-8') as local_file:
                            local_content = local_file.read()
                        with open(temp_path, 'r', encoding='utf-8') as temp_file:
                            remote_content = temp_file.read()
                        
                        if local_content != remote_content:
                            update_required = True
                    else:
                        update_required = True # File doesn't exist locally

                    if update_required:
                        shutil.copy(temp_path, local_path)
                        print(f"Updated/Downloaded {local_path} from GitHub.")
                    
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            except Exception as e:
                print(f"Error checking for updates for {local_path}: {e}")

    def set_windows11_dark_theme(self):
        app = QApplication.instance()
        
        if sys.platform == "win32":
            try:
                from ctypes import windll, byref, sizeof, c_int
                hwnd = int(self.winId())
                for attribute in [19, 20]:
                    try:
                        value = c_int(1)
                        windll.dwmapi.DwmSetWindowAttribute(
                            hwnd,
                            attribute,
                            byref(value),
                            sizeof(value)
                        )
                    except Exception as e:
                        print(f"Dark title bar not supported (attribute {attribute}): {e}")
            except Exception as e:
                print(f"Dark title bar initialization failed: {e}")

        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(32, 32, 32))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.Text, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(120, 120, 120))

        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(127, 127, 127))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(127, 127, 127))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(127, 127, 127))

        app.setPalette(palette)

        self.setStyleSheet("""
            QWidget {
                background-color: #202020;
                color: #f0f0f0;
                font-family: "Segoe UI", Arial, sans-serif;
                font-size: 9pt;
            }
            QPushButton {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 5px 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #1d1d1d;
            }
            QScrollArea {
                border: none;
            }
            QLineEdit {
                background-color: #252525;
                color: #f0f0f0;
                padding: 5px;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                selection-background-color: #3a6ea5;
                selection-color: #ffffff;
            }
            QLineEdit:disabled {
                background-color: #1a1a1a;
                color: #7f7f7f;
            }
            QProgressDialog {
                background-color: #202020;
                color: #f0f0f0;
            }
            QProgressBar {
                background-color: #252525;
                color: #f0f0f0;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3a6ea5;
                border-radius: 3px;
            }
            QLabel {
                color: #f0f0f0;
            }
            QMessageBox {
                background-color: #202020;
            }
            QMessageBox QLabel {
                color: #f0f0f0;
            }
            QScrollBar:vertical {
                border: none;
                background: #252525;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #0077be;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical {
                border: none;
                background: none;
                height: 0px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
            }
            QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
                subcontrol-position: top;
                subcontrol-origin: margin;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                border: none;
                background: #252525;
                height: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:horizontal {
                background: #0077be;
                min-width: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
            QTableWidget {
                gridline-color: #3d3d3d;
                border: none;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #f0f0f0;
                padding: 5px;
                border: none;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)

    def load_character_map(self):
        character_map = {}
        csv_files = ["Codes_and_Names.csv", "Codes_and_Names_EventLobby.csv"]
        for file_path in csv_files:
            if not os.path.exists(file_path):
                continue
            try:
                with open(file_path, newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        character_map[row['ID']] = {
                            'character': row['CHARACTER'],
                            'id': row['ID']
                        }
            except Exception as e:
                print(f"Error loading character map from {file_path}: {e}")
        return character_map

    def load_settings(self):
        default_settings = {
            "mods_folder": ""
        }
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading settings: {e}")
        return default_settings

    def load_naps_settings(self):
        default_settings = {
            "naps_folder": ""
        }
        try:
            if os.path.exists(self.naps_settings_file):
                with open(self.naps_settings_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading NAPS settings: {e}")
        return default_settings

    def save_settings(self):
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def save_naps_settings(self):
        try:
            with open(self.naps_settings_file, 'w') as f:
                json.dump(self.naps_settings, f, indent=4)
        except Exception as e:
            print(f"Error saving NAPS settings: {e}")

    def extract_info_from_filename(self, filename):
        basename = os.path.splitext(filename)[0]
        
        info = {
            'character': 'Unknown',
            'id': 'Unknown',
            'author': 'Unknown',
            'skin': 'N/A',
            'type': 'Unknown',
            'mod_name': 'Unknown',
            'extension': os.path.splitext(filename)[1]
        }
        
        try:
            # Split filename by hyphen, the new delimiter
            parts = basename.split('-')
            
            if not parts:
                return info

            mod_id = parts[0]
            is_event_mod = mod_id.startswith("eventscene_") or mod_id.startswith("eventtitle_")

            # Event Mod format: [ID]-[type]-[Author]-[ModName]
            # Example: eventtitle_neverland_02-lobby-Na0h-NudeWaifusOnsen
            if is_event_mod and len(parts) >= 4:
                info['id'] = mod_id
                info['type'] = parts[1]
                info['author'] = parts[2]
                info['mod_name'] = ' '.join(parts[3:])
            
            # Standard Mod format: [ID]-[skin_code]-[type]-[Author]-[ModName]
            # Example: c470-00-lobby-Hiccup-RedHoodHalfNude
            elif not is_event_mod and len(parts) >= 5:
                info['id'] = mod_id
                info['skin'] = parts[1]
                info['type'] = parts[2]
                info['author'] = parts[3]
                info['mod_name'] = ' '.join(parts[4:])
            
            if info['id'] in self.character_map:
                info['character'] = self.character_map[info['id']]['character']
                
        except Exception as e:
            print(f"Error parsing filename {filename}: {e}")
        
        return info

    def browse_mods_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Mods Folder", os.path.expanduser("~"),
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.folder_edit.setText(folder)
            self.settings["mods_folder"] = folder
            self.save_settings()
            self.load_mods()

    def browse_naps_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select NAPS Folder", os.path.expanduser("~"),
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.naps_edit.setText(folder)
            self.naps_settings["naps_folder"] = folder
            self.save_naps_settings()
            self.load_mods()

    def folder_path_changed(self, text):
        self.settings["mods_folder"] = text
        self.save_settings()
        self.load_mods()

    def naps_path_changed(self, text):
        self.naps_settings["naps_folder"] = text
        self.save_naps_settings()
        self.load_mods()

    def verify_mods_folder(self):
        if not self.settings.get("mods_folder") or not os.path.exists(self.settings["mods_folder"]):
            QMessageBox.information(
                self, "Select Mods Folder",
                "Please enter or browse your mods folder path and naps folder path",
                QMessageBox.StandardButton.Ok
            )
        else:
            self.load_mods()

    def get_naps_file_size(self, file_id):
        naps_folder = self.naps_settings.get("naps_folder", "")
        if not naps_folder or not os.path.exists(naps_folder):
            return None

        for root, _, files in os.walk(naps_folder):
            for file in files:
                if file == file_id:
                    file_path = os.path.join(root, file)
                    return os.path.getsize(file_path)
        return None

    def check_mod_status(self, mod_info, mod_path):
        mod_size = os.path.getsize(mod_path)
        mod_id = mod_info['id']
        skin_code = mod_info['skin']
        mod_type = mod_info['type'].lower()
        is_event_mod = mod_id.startswith("eventscene_") or mod_id.startswith("eventtitle_")

        for char_data in self.character_data:
            # Match condition for event mods (ID only)
            is_match = is_event_mod and char_data.get('ID') == mod_id
            # Match condition for standard mods (ID and skin_code)
            if not is_event_mod:
                is_match = char_data.get('ID') == mod_id and char_data.get('skin_code') == skin_code

            if is_match:
                # Event mods are always lobby type, standard mods can be lobby or burst
                target_id_key = "lobby_id" if is_event_mod else f"{mod_type}_id"
                if target_id_key in char_data:
                    target_id = char_data[target_id_key]
                    naps_size = self.get_naps_file_size(target_id)
                    if naps_size and naps_size == mod_size:
                        return "Active"
                # Found the character, no need to continue loop
                return "Inactive"
        return "Inactive"

    def load_mods(self):
        mods_folder = self.settings.get("mods_folder", "")
        self.table_widget.setRowCount(0)
        
        if mods_folder and os.path.exists(mods_folder):
            # Store full filenames to avoid reconstruction issues
            self.mod_files = {str(i): f for i, f in enumerate(os.listdir(mods_folder)) if not os.path.isdir(os.path.join(mods_folder, f)) and not f.startswith('.') and not f.endswith('.json')}
            
            for index, original_name in self.mod_files.items():
                item_path = os.path.join(mods_folder, original_name)
                self.add_mod_item(original_name, item_path, index)

    def add_mod_item(self, original_name, file_path, index):
        row_position = self.table_widget.rowCount()
        self.table_widget.insertRow(row_position)
        
        info = self.extract_info_from_filename(original_name)
        status = self.check_mod_status(info, file_path)
        
        author_item = QTableWidgetItem(info['author'])
        author_item.setData(Qt.ItemDataRole.UserRole, index) # Store original index
        author_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_widget.setItem(row_position, 0, author_item)
        
        id_item = QTableWidgetItem(info['id'])
        id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_widget.setItem(row_position, 1, id_item)
        
        character_item = QTableWidgetItem(info['character'])
        character_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_widget.setItem(row_position, 2, character_item)
        
        skin_item = QTableWidgetItem(info['skin'])
        skin_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_widget.setItem(row_position, 3, skin_item)
        
        mod_name_item = QTableWidgetItem(info['mod_name'])
        mod_name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_widget.setItem(row_position, 4, mod_name_item)
        
        type_name = info['type'].capitalize()
        type_item = QTableWidgetItem(type_name)
        type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table_widget.setItem(row_position, 5, type_item)
        
        status_item = QTableWidgetItem(status)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Set text color based on status
        if status == "Active":
            status_item.setForeground(QColor("#008080"))  # Teal
        elif status == "Inactive":
            status_item.setForeground(QColor("#FA8072"))  # Salmon
            
        self.table_widget.setItem(row_position, 6, status_item)
        
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(5, 0, 5, 0)
        actions_layout.setSpacing(5)
        
        preview_btn = QPushButton("Preview")
        preview_btn.clicked.connect(lambda _, p=file_path: self.preview_file(p))
        actions_layout.addWidget(preview_btn)

        if status == "Inactive":
            activate_btn = QPushButton("Activate")
            activate_btn.clicked.connect(lambda _, r=row_position: self.activate_mod(r))
            actions_layout.addWidget(activate_btn)
        else:
            deactivate_btn = QPushButton("Deactivate")
            deactivate_btn.clicked.connect(lambda _, r=row_position: self.deactivate_mod(r))
            actions_layout.addWidget(deactivate_btn)
        
        actions_layout.addStretch()
        actions_widget.setLayout(actions_layout)
        self.table_widget.setCellWidget(row_position, 7, actions_widget)
        
        self.table_widget.setRowHeight(row_position, 45)

    def activate_mod(self, row):
        author_item = self.table_widget.item(row, 0)
        file_index = author_item.data(Qt.ItemDataRole.UserRole)
        original_filename = self.mod_files.get(file_index)

        if not original_filename:
            QMessageBox.warning(self, "Error", "Could not find mod file reference.")
            return

        mods_folder = self.settings.get("mods_folder", "")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        temp_renaming = os.path.join(script_dir, "temp-renaming")
        
        try:
            # Store current scroll position
            scroll_value = self.table_widget.verticalScrollBar().value()

            original_path = os.path.join(mods_folder, original_filename)
            if not os.path.exists(original_path):
                QMessageBox.warning(self, "Error", f"Could not find mod file: {original_filename}")
                return

            os.makedirs(temp_renaming, exist_ok=True)

            for existing_file in os.listdir(temp_renaming):
                file_path = os.path.join(temp_renaming, existing_file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"Failed to delete {file_path}: {e}")

            shutil.copy2(original_path, temp_renaming)

            rename_script = os.path.join(script_dir, "1_rename-temprenaming.py")
            if os.path.exists(rename_script):
                subprocess.run([sys.executable, rename_script], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                QMessageBox.warning(self, "Error", "Rename script not found")
                return

            compare_script = os.path.join(script_dir, "2_compare_copy_replace.py")
            if os.path.exists(compare_script):
                subprocess.run([sys.executable, compare_script], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                QMessageBox.warning(self, "Error", "Compare script not found")
                return

            QMessageBox.information(self, "Success", "Mod activated successfully!")
            self.load_mods()
            self.filter_mods() # Re-apply filter
            
            # Restore scroll position after reload and filter
            self.table_widget.verticalScrollBar().setValue(scroll_value)

        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"A script failed to execute: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Activation failed: {str(e)}")
        finally:
            if os.path.exists(temp_renaming):
                shutil.rmtree(temp_renaming, ignore_errors=True)

    def deactivate_mod(self, row):
        id_item = self.table_widget.item(row, 1)
        skin_item = self.table_widget.item(row, 3)
        type_item = self.table_widget.item(row, 5)
        author_item = self.table_widget.item(row, 0)
        file_index = author_item.data(Qt.ItemDataRole.UserRole)
        original_mod_filename = self.mod_files.get(file_index)

        if not original_mod_filename:
            QMessageBox.warning(self, "Error", "Could not find mod file reference.")
            return

        script_dir = os.path.dirname(os.path.abspath(__file__))
        mods_folder = self.settings.get("mods_folder", "")
        naps_folder = self.naps_settings.get("naps_folder", "")
        temp_download_dir = os.path.join(script_dir, "temp-download")

        if not naps_folder or not os.path.isdir(naps_folder):
            QMessageBox.warning(self, "Error", "NAPS folder path is not set or invalid.")
            return

        os.makedirs(temp_download_dir, exist_ok=True)

        try:
            # Store current scroll position
            scroll_value = self.table_widget.verticalScrollBar().value()

            mod_id = id_item.text()
            skin_code = skin_item.text()
            mod_type = type_item.text().lower()
            is_event_mod = mod_id.startswith("eventscene_") or mod_id.startswith("eventtitle_")

            download_url = None
            target_hash = None
            url_data = self.character_url_data

            # Find URL and HASH
            for i, char_data in enumerate(self.character_data):
                match = False
                if is_event_mod and char_data.get('ID') == mod_id:
                    match = True
                elif not is_event_mod and char_data.get('ID') == mod_id and char_data.get('skin_code') == skin_code:
                    match = True

                if match:
                    hash_key = 'lobby_id' if is_event_mod else f"{mod_type}_id"
                    target_hash = char_data.get(hash_key)
                    # Now find the corresponding URL
                    for char_url_data in url_data:
                        url_match = False
                        if is_event_mod and char_url_data.get('ID') == mod_id:
                             url_match = True
                        elif not is_event_mod and char_url_data.get('ID') == mod_id and char_url_data.get('skin_code') == skin_code:
                             url_match = True
                        
                        if url_match:
                            download_url = char_url_data.get(hash_key)
                            break
                    break
            
            if not download_url:
                QMessageBox.warning(self, "Error", "Could not find the download URL for the original file.")
                return
            if not target_hash:
                QMessageBox.warning(self, "Error", "Could not determine the original file hash name.")
                return

            # Download original file
            downloaded_file_basename = os.path.basename(download_url).split('?')[0]
            download_path = os.path.join(temp_download_dir, downloaded_file_basename)
            
            progress_dialog = QProgressDialog("Downloading original file...", "Cancel", 0, 100, self)
            progress_dialog.setWindowTitle("Downloading")
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)

            def update_progress(count, block_size, total_size):
                if total_size > 0:
                    progress = int(count * block_size * 100 / total_size)
                    progress_dialog.setValue(progress)
                QApplication.processEvents()

            urllib.request.urlretrieve(download_url, download_path, reporthook=update_progress)
            progress_dialog.setValue(100)

            # Rename downloaded file to its hash and replace in NAPS
            renamed_path = os.path.join(temp_download_dir, target_hash)
            os.rename(download_path, renamed_path)
            
            found_and_replaced = False
            for root, _, files in os.walk(naps_folder):
                if target_hash in files:
                    target_path = os.path.join(root, target_hash)
                    shutil.move(renamed_path, target_path)
                    found_and_replaced = True
                    break
            
            if found_and_replaced:
                QMessageBox.information(self, "Success", "Original file restored successfully.")
                self.load_mods()
                self.filter_mods()
                # Restore scroll position after reload and filter
                self.table_widget.verticalScrollBar().setValue(scroll_value)
            else:
                QMessageBox.warning(self, "Error", f"Could not find matching file hash '{target_hash}' in NAPS folder.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to deactivate mod: {str(e)}")
        finally:
            shutil.rmtree(temp_download_dir, ignore_errors=True)


    def filter_mods(self):
        search_text = self.search_edit.text().lower()
        
        for row in range(self.table_widget.rowCount()):
            match = False
            for col in range(self.table_widget.columnCount() - 1): # Exclude actions column
                item = self.table_widget.item(row, col)
                if item and search_text in item.text().lower():
                    match = True
                    break
            
            self.table_widget.setRowHidden(row, not match)

    def clear_search(self):
        self.search_edit.clear()

    def preview_file(self, file_path):
        if file_path.endswith('.skel') or file_path.endswith('.json'):
            self.preview_animation(file_path)
        else:
            self.extract_and_preview(file_path)

    def extract_and_preview(self, bundle_path):
        spine_assets_dir = self.get_spine_assets_dir()
        self.progress_dialog = QProgressDialog(
            f"Loading assets from {os.path.basename(bundle_path)}...",
            "Cancel", 0, 100, self)
        self.progress_dialog.setWindowTitle("Loading Assets")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setAutoReset(False)
        self.progress_dialog.canceled.connect(self.cancel_extraction)

        self.current_extraction = AssetExtractor(bundle_path, spine_assets_dir)
        self.current_extraction.progress_signal.connect(self.update_progress)
        self.current_extraction.finished_signal.connect(self.extraction_complete)
        self.current_extraction.start()

        self.progress_dialog.show()

    def update_progress(self, value, message):
        if self.progress_dialog:
            self.progress_dialog.setValue(value)
            self.progress_dialog.setLabelText(message)

    def cancel_extraction(self):
        if self.current_extraction and self.current_extraction.isRunning():
            self.current_extraction.cancel()
        if self.progress_dialog:
            self.progress_dialog.close()
        self.progress_dialog = None

    def extraction_complete(self, output_dir, skel_path, message):
        if self.progress_dialog:
            self.progress_dialog.close()
        if skel_path:
            self.preview_animation(skel_path)
        else:
            if output_dir:
                QMessageBox.warning(
                    self, "Extraction Complete",
                    f"{message}\n\nExtracted assets to:\n{output_dir}",
                    QMessageBox.StandardButton.Ok
                )
            else:
                QMessageBox.critical(
                    self, "Extraction Failed",
                    message,
                    QMessageBox.StandardButton.Ok
                )

    def preview_animation(self, animation_path):
        viewer_path = os.path.join(os.path.dirname(__file__), "SpineViewer-anosu", "SpineViewer.exe")
        
        if not os.path.exists(viewer_path):
            QMessageBox.critical(
                self, "Error",
                f"Spine Viewer not found at path: {viewer_path}",
                QMessageBox.StandardButton.Ok
            )
            return

        try:
            # Use CREATE_NO_WINDOW flag for subprocess on Windows
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW

            subprocess.Popen(
                [viewer_path, animation_path],
                creationflags=creation_flags
            )
            
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Failed to launch Spine Viewer:\n{str(e)}",
                QMessageBox.StandardButton.Ok
            )

    def closeEvent(self, event):
        shutil.rmtree(self.get_spine_assets_dir(), ignore_errors=True)
        event.accept()

    def get_spine_assets_dir(self):
        spine_dir = os.path.join(tempfile.gettempdir(), "SpineAssets")
        os.makedirs(spine_dir, exist_ok=True)
        return spine_dir

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    icon_path = "icon.png"
    if getattr(sys, 'frozen', False):
        icon_path = os.path.join(sys._MEIPASS, icon_path)

    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    viewer = SpineViewer()
    viewer.show()
    sys.exit(app.exec())