from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from NotionHelper import *
import requests
import webbrowser
import sys
import csv
import os

APP_VERSION = "1.0.1" 
GITHUB_REPO = "da-penguin-guy/Filemaker-Notion-Helper"

threads = {}

class Worker(QObject):
    finished = pyqtSignal()
    result = pyqtSignal(object)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    @pyqtSlot()
    def run(self):
        result = self.func(*self.args, **self.kwargs)
        self.result.emit(result)
        self.finished.emit()

class FileDropLabel(QLabel):
    """Custom QLabel that accepts file drag-and-drop for specific file extensions."""

    def __init__(self, text: str = "Drop a file here", accepted_extensions: list = None):
        """
        Set up the label to accept drops and style it.
        accepted_extensions: list of allowed file extensions (e.g., ['.csv', '.tsv'])
        """
        super().__init__(text)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dropped_file_path = None
        self.accepted_extensions = accepted_extensions if accepted_extensions else ['.csv']
        # Make it bigger and stand out visually
        self.setMinimumSize(200, 100)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #0078d7;
                color: #0078d7;
                font-size: 18px;
                font-weight: bold;
                border-radius: 10px;
            }
        """)

    def dragEnterEvent(self, event) -> None:
        """Accept drag if it contains URLs (files)."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        """Handle file drop, only accept files with allowed extensions."""
        if event.mimeData().hasUrls():
            file_path = event.mimeData().urls()[0].toLocalFile()
            # Check if the file extension is in the accepted list
            if any(file_path.lower().endswith(ext.lower()) for ext in self.accepted_extensions) or self.accepted_extensions == None:
                self.setText(f"File: {file_path}")
                self.dropped_file_path = file_path
            else:
                ShowError(f"Please drop a valid file: {', '.join(self.accepted_extensions)}")

class SearchableComboBox(QComboBox):
    """A QComboBox with live search/filtering capability."""

    def __init__(self, parent=None):
        """Set up editable combo box and connect search logic."""
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.lineEdit().textEdited.connect(self.filter_items)
        self.all_items = []

    def showPopup(self) -> None:
        """Show the dropdown and focus the search bar."""
        super().showPopup()
        self.lineEdit().setFocus()

    def addItems(self, items: list) -> None:
        """Add items to the combo box and store all for filtering."""
        super().clear()
        self.all_items = items
        for item in items:
            if isinstance(item, tuple) and len(item) == 2:
                self.addItem(item[0], item[1])
            else:
                self.addItem(item)

    def filter_items(self, text: str) -> None:
        """Filter items based on the search text."""
        self.blockSignals(True)
        current_text = self.lineEdit().text()
        self.clear()
        for item in self.all_items:
            if text.lower() in str(item).lower():
                if isinstance(item, tuple) and len(item) == 2:
                    self.addItem(item[0], item[1])
                else:
                    self.addItem(item)
        self.setEditText(current_text)
        self.blockSignals(False)
        # Do NOT call self.showPopup() here!

class Console(QTextEdit):
    """A read-only text console for logging output and errors."""

    def __init__(self, parent=None):
        """Set up the console appearance and make it read-only."""
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet("font-family: monospace; font-size: 14px; padding: 10px;")
        self.setMinimumHeight(200)

    def Log(self, text: str) -> None:
        """Append normal log text to the console."""
        super().append(text)
        self.moveCursor(QTextCursor.MoveOperation.End)

    def Error(self, text: str) -> None:
        """Append error text in red to the console."""
        self.setTextColor(Qt.GlobalColor.red)
        self.Log(text)
        self.setTextColor(Qt.GlobalColor.white)


def CreateHarevestLayout(layout: QVBoxLayout) -> None:
    """Create the layout for the Harvest Processor tab."""
    # Create the file drop area
    fileDrop = FileDropLabel("Drag the CSV file here", ['.csv', '.tsv'])
    # Create the process button
    btn = QPushButton("Process Harvest")
    btn.setMinimumSize(150, 50)
    btn.setStyleSheet("font-size: 18px; font-weight: bold; padding: 12px;")

    # Create the console for output
    console = Console()

    # Create a horizontal layout to split left and right
    hLayout = QHBoxLayout()
    leftLayout = QVBoxLayout()
    # Add file drop and button to the left side
    leftLayout.addWidget(fileDrop)
    leftLayout.addWidget(btn)
    leftLayout.addStretch(1)  # Push widgets to the top
    # Assign the left layout with 1/3 of the width
    hLayout.addLayout(leftLayout, 1)
    # Assign the console to the right side with 2/3 of the width
    hLayout.addWidget(console, 2)
    layout.addLayout(hLayout)

    def OnButtonClicked() -> None:
        """Handle the process button click event."""
        if fileDrop.dropped_file_path:
            console.Log(f"Processing: {fileDrop.dropped_file_path}")
            try:
                ProcessHarvest(fileDrop.dropped_file_path, console)
                console.Log("Done!")
            except Exception as e:
                console.Error(f"Error: {e}")
        else:
            ShowError("No file selected.")
    btn.clicked.connect(OnButtonClicked)

def ProcessHarvest(filePath: str, console: Console) -> None:
    """Process the CSV file: rename files and export as TSV."""
    dir = os.path.dirname(filePath)
    with open(filePath, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            newName = ""
            try:
                newName = row["TRACK: Audio Filename"]
            except Exception as e:
                try:
                    newName = row["HARVEST TRACK: Audio Filename"]
                except Exception as e:
                    console.Error("Filename header not found in CSV file.")
                    return
            splitName = newName.split("_")
            oldName = f"{splitName[2]}_{splitName[3]}"
            try:
                os.rename(os.path.join(dir,oldName), os.path.join(dir,newName))
                console.Log(f"Renamed {oldName} to {newName}")
            except Exception as e:
                console.Error(f"Error renaming {oldName} to {newName}: {e}")
    base, _ = os.path.splitext(filePath)
    outputPath = base + ".txt"

    # Write the CSV as TSV
    with open(filePath, newline='', encoding='utf-8') as csvfile, \
        open(outputPath, 'w', newline='', encoding='utf-8') as tsvfile:
        reader = csv.reader(csvfile)
        writer = csv.writer(tsvfile, delimiter='\t')
        for row in reader:
            writer.writerow(row)

    console.Log(f"TSV file written to: {outputPath}")


def CreateVersionsLayout(layout: QVBoxLayout) -> None:
    """Create the layout for the Version Adder tab."""
    # Create searchable dropdown for Notion pages
    SelectBox = SearchableComboBox()
    SelectBox.setMinimumWidth(200)
    SelectBox.setPlaceholderText("Search for a track")

    # --- Notion integration ---
    tracksDatabase = "12bcc95908f4804b8486cb3c4272fa17"
    notionData = ReadNotionDatabase(tracksDatabase)

    # Build a list of (page_title, page_id) pairs for the dropdown
    items = []
    if notionData and "results" in notionData:
        for page in notionData["results"]:
            props = page.get("properties", {})
            pageId = page.get("id", "")
            trackTitleProp = props.get("TrackTitle", {})
            if trackTitleProp.get("type") == "title":
                titleItems = trackTitleProp.get("title", [])
                if titleItems and "plain_text" in titleItems[0]:
                    pageTitle = titleItems[0]["plain_text"]
                elif titleItems:
                    pageTitle = titleItems[0].get("text", {}).get("content", "")
                else:
                    pageTitle = "(No Title)"
            else:
                pageTitle = "(No Title)"
            items.append((pageTitle, pageId))
    else:
        ShowError("Failed to load tracks from Notion. Please check your connection or database ID.")
        return
    
    SelectBox.addItems(items)

    # Create the upload button
    btn = QPushButton("Upload Mixouts")
    btn.setMinimumSize(150, 50)
    btn.setStyleSheet("font-size: 18px; font-weight: bold; padding: 12px;")

    # Create the console for output
    console = Console()

    # Create 5 small text boxes for the left side for mixout input
    leftSideInputs = QVBoxLayout()
    textBoxes = []
    for _ in range(5):
        tb = QLineEdit()
        tb.setMaximumWidth(300)
        altSuffix = "Alt" if _ == 0 else f"Alt {_ + 1}"
        tb.setPlaceholderText("Enter Mixout for " + altSuffix)
        leftSideInputs.addWidget(tb)
        textBoxes.append((tb, altSuffix))
    leftSideInputs.addStretch(1)

    # Add a vertical spacer before the album layout
    spacer = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

    albumDisplay = QLineEdit()
    albumDisplay.setReadOnly(True)
    albumDisplay.setPlaceholderText("")
    albumDisplay.setMinimumHeight(32)
    albumDisplay.setStyleSheet("font-size: 16px;")

    #Create a horizontal layout for the label and album display
    albumLayout = QHBoxLayout()
    albumLabel = QLabel("Album:")
    albumLabel.setMinimumWidth(120)
    albumLabel.setStyleSheet("font-size: 16px; font-weight: bold;")
    albumLayout.addWidget(albumLabel)
    albumLayout.addWidget(albumDisplay, stretch=1)

    def UpdateRelationField() -> None:
        if not SelectBox.currentData():
            albumDisplay.setText("")
            return
        pageId = SelectBox.currentData()
        pageProperties = ReadPageProperties(pageId)
        albumId = pageProperties["Album"]["relation"][0]["id"]
        albumProperties = ReadPageProperties(albumId)
        albumName = albumProperties["Working Title"]["title"][0]["text"]["content"]
        albumDisplay.setText(albumName)

    SelectBox.currentIndexChanged.connect(UpdateRelationField)

    # Main left layout (inputs + dropdown + button)
    leftLayout = QVBoxLayout()
    leftLayout.addWidget(SelectBox)
    leftLayout.addLayout(leftSideInputs)
    leftLayout.addWidget(btn)
    leftLayout.addItem(spacer)           # <-- Add vertical space before album layout
    leftLayout.addLayout(albumLayout)    # <-- Add the album label + display here
    leftLayout.addStretch(1)

    # Horizontal layout: left (inputs, dropdown, button) | right (console)
    hLayout = QHBoxLayout()
    hLayout.addLayout(leftLayout, 2)
    hLayout.addWidget(console, 2)

    layout.addLayout(hLayout)

    def OnUploadClicked() -> None:
        """Handle the upload button click event."""
        versions = []
        for box, suffix in textBoxes:
            if box.text() or box.text() != "":
                versions.append((box.text(), suffix))
        selectedPageId = SelectBox.currentData()
        if selectedPageId:
            AddVersions(selectedPageId, SelectBox.currentText(), versions, console)
        else:
            ShowError("Please select a track.")

        console.Log(f"Uploaded versions for {SelectBox.currentText()}")
        for box, suffix in textBoxes:
            box.clear()

    btn.clicked.connect(OnUploadClicked)

def AddVersions(pageID: str, pageName: str, versions: list, console: Console) -> None:
    """Add mixout versions to the Notion database for the selected track."""
    versionDatabase = "200cc95908f480429e51d92a661a9102"
    for mixout, alt in versions:
        newProperties = {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": f"{pageName}_{alt}"
                        }
                    }
                ]
            },
            "Mixout": {
                "rich_text": [
                    {
                        "text": {
                            "content": mixout
                        }
                    }
                ]
            },
            "Version": {
                "select": {
                    "name": alt
                }
            },
            "Track Title": {
                "relation": [
                    {"id": pageID}
                ]
            }
        }
        CreateNotionPage(versionDatabase, newProperties)
        console.Log(f"Uploaded versions {alt} for {pageName}: {mixout}")


def CreateImportLayout(layout: QVBoxLayout) -> None:
    albumList = QListWidget()
    albumList.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

    DATABASE_ID = "4ce7b4cefa8d4478b197dd9e50e69421"
    notionData = ReadNotionDatabase(DATABASE_ID)

    if notionData and "results" in notionData:
        for page in notionData["results"]:
            props = page.get("properties", {})
            trackTitleProp = props.get("Working Title", {})
            if trackTitleProp.get("type") == "title":
                titleItems = trackTitleProp.get("title", [])
                if titleItems and "plain_text" in titleItems[0]:
                    pageTitle = titleItems[0]["plain_text"]
                elif titleItems:
                    pageTitle = titleItems[0].get("text", {}).get("content", "")
                else:
                    pageTitle = "(No Title)"
            else:
                pageTitle = "(No Title)"
            # Create QListWidgetItem and store pageId in UserRole
            item = QListWidgetItem(pageTitle)
            item.setData(Qt.ItemDataRole.UserRole, page)
            albumList.addItem(item)
    else:
        ShowError("Failed to load tracks from Notion. Please check your connection or database ID.")
        return

    btn = QPushButton("Process Albums")
    btn.setMinimumSize(150, 50)
    btn.setStyleSheet("font-size: 18px; font-weight: bold; padding: 12px;")
    console = Console()
    hLayout = QHBoxLayout()
    leftLayout = QVBoxLayout()
    leftLayout.addWidget(QLabel("Select Albums to Export:"))
    leftLayout.addWidget(albumList)
    leftLayout.addWidget(btn)
    leftLayout.addStretch(1)
    hLayout.addLayout(leftLayout, 1)
    hLayout.addWidget(console, 2)
    layout.addLayout(hLayout)

    def OnButtonClicked():
        dirPath = QFileDialog.getExistingDirectory(None, "Select Output Directory")
        # To get a list of (name, id) tuples for selected albums:
        selectedAlbums = [
            (item.text(), item.data(Qt.ItemDataRole.UserRole))
            for item in albumList.selectedItems()
        ]
        if not dirPath:
            console.Log("Export cancelled by user.")
            return
        console.Log(f"Saving output to: {dirPath}")
        thread = QThread()
        worker = Worker(ProcessImport, dirPath, console, selectedAlbums)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        # Store references so they are not garbage collected
        threads["import"] = (thread, worker)
        thread.start()

    btn.clicked.connect(OnButtonClicked)

def ProcessImport(dirPath: str, console: Console, selectedAlums : list[tuple]) -> None:
    """Gets data from Notion and exports it to CSV files."""

    def GetListValue(properties, propertyName):
        values = [v["name"] for v in properties[propertyName]["multi_select"]]
        return "\n".join(values) if values else ""

    DATABASE_ID = "4ce7b4cefa8d4478b197dd9e50e69421"
    data = ReadNotionDatabase(DATABASE_ID)

    albumsFile = open(os.path.join(dirPath, "albums.csv"), "w", newline='', encoding='utf-8')
    tracksFile = open(os.path.join(dirPath, "tracks.csv"), "w", newline='', encoding='utf-8')
    versionsFile = open(os.path.join(dirPath, "versions.csv"), "w", newline='', encoding='utf-8')
    moodsFile = open(os.path.join(dirPath, "moods.csv"), "w", newline='', encoding='utf-8')
    genresFile = open(os.path.join(dirPath, "genres.csv"), "w", newline='', encoding='utf-8')
    miscFile = open(os.path.join(dirPath, "misc.csv"), "w", newline='', encoding='utf-8')
    composersFile = open(os.path.join(dirPath, "composers.csv"), "w", newline='', encoding='utf-8')
    contentProvidersFile = open(os.path.join(dirPath, "contentProviders.csv"), "w", newline='', encoding='utf-8')

    albumWriter = csv.writer(albumsFile)
    albumWriter.writerow(["AlbumTitle", "AlbumID", "UpdateID"])
    trackWriter = csv.writer(tracksFile)
    trackWriter.writerow([
        "TrackTitle", "UniqueTitleID", "AlbumID", "Track Description",
        "Key", "BPM",
        "Composer 1", "Composer 2", "Content Provider 1", "Content Provider 2",
        "InstGroup Rhythm", "InstGroup Bass", "InstGroup Guitar",
        "InstGroup Keys", "InstGroup Strings", "InstGroup Woodwinds",
        "InstGroup Brass", "InstGroup Misc"
    ])
    versionWriter = csv.writer(versionsFile)
    versionWriter.writerow(["UniqueTitleID", "Mixout", "Version", "Duration"])
    moodWriter = csv.writer(moodsFile)
    moodWriter.writerow(["UniqueTitleID", "Moods"])
    genreWriter = csv.writer(genresFile)
    genreWriter.writerow(["UniqueTitleID", "TrackGenre"])
    miscWriter = csv.writer(miscFile)
    miscWriter.writerow(["UniqueTitleID", "Misc"])
    composerWriter = csv.writer(composersFile)
    composerWriter.writerow(["ComposerID", "UniqueTitleID"])
    contentProviderWriter = csv.writer(contentProvidersFile)
    contentProviderWriter.writerow(["CPID", "UniqueTitleID"])

    for name, albumData in selectedAlums:
        albumProperties = albumData["properties"]
        albumInfo = [
            name,
            albumProperties["AlbumID"]["rich_text"][0]["plain_text"] if albumProperties["AlbumID"]["rich_text"] else "",
            albumProperties["Release"]["rich_text"][0]["plain_text"] if albumProperties["Release"]["rich_text"] else ""
        ]
        albumWriter.writerow(albumInfo)
        console.Log(f"Processing album: {albumInfo[0]}")

        for track in albumProperties["Track Submission Form"]["relation"]:
            trackProperties = ReadPageProperties(track["id"])
            trackId = trackProperties["Unique Title Id"]["unique_id"]["prefix"] + str(trackProperties["Unique Title Id"]["unique_id"]["number"])

            if len(trackProperties["Content Provider 1"]["relation"]) > 0:
                contentProviderWriter.writerow([ReadPageProperties(trackProperties["Content Provider 1"]["relation"][0]["id"])["CPID"]["rich_text"][0]["plain_text"], trackId])
            if len(trackProperties["Content Provider 2"]["relation"]) > 0:
                contentProviderWriter.writerow([ReadPageProperties(trackProperties["Content Provider 2"]["relation"][0]["id"])["CPID"]["rich_text"][0]["plain_text"], trackId])
            if len(trackProperties["Composer 1"]["relation"]) > 0:
                composerPage = ReadPageProperties(trackProperties["Composer 1"]["relation"][0]["id"])
                if(len(composerPage["ComposerID"]["rich_text"]) <= 0):
                    console.Error(f"Composer 1 ID not found for track: {trackProperties['TrackTitle']['title'][0]['text']['content']}")
                else:
                    composerWriter.writerow([composerPage["ComposerID"]["rich_text"][0]["plain_text"], trackId])
            if len(trackProperties["Composer 2"]["relation"]) > 0:
                composerPage = ReadPageProperties(trackProperties["Composer 2"]["relation"][0]["id"])
                if(len(composerPage["ComposerID"]["rich_text"]) <= 0):
                    console.Error(f"Composer 2 ID not found for track: {trackProperties['TrackTitle']['title'][0]['text']['content']}")
                else:
                    composerWriter.writerow([composerPage["ComposerID"]["rich_text"][0]["plain_text"], trackId])

            track_info = [
                trackProperties["TrackTitle"]["title"][0]["text"]["content"],
                trackId,
                albumInfo[1],
                trackProperties["Track Description"]["rich_text"][0]["plain_text"] if trackProperties["Track Description"]["rich_text"] else "",
                trackProperties["key"]["rich_text"][0]["plain_text"] if trackProperties["key"]["rich_text"] else "",
                trackProperties["Tempo"]["rich_text"][0]["plain_text"] if trackProperties["Tempo"]["rich_text"] else "",
                GetListValue(trackProperties, "InstGroup Rhythm"),
                GetListValue(trackProperties, "InstGroup Bass"),
                GetListValue(trackProperties, "InstGroup Guitar"),
                GetListValue(trackProperties, "InstGroup Keys"),
                GetListValue(trackProperties, "InstGroup Strings"),
                GetListValue(trackProperties, "InstGroup Woodwinds"),
                GetListValue(trackProperties, "InstGroup Brass"),
                GetListValue(trackProperties, "InstGroup Misc"),
            ]

            moodWriter.writerow([track_info[1], GetListValue(trackProperties, "Moods")])
            genreWriter.writerow([track_info[1], GetListValue(trackProperties, "TrackGenre")])
            miscWriter.writerow([track_info[1], GetListValue(trackProperties, "Misc")])

            trackWriter.writerow(track_info)
            trackLength = trackProperties["Track Duration"]["rich_text"][0]["plain_text"] if trackProperties["Track Duration"]["rich_text"] else ""

            console.Log(f"Processing track: {track_info[0]}")
            full = [
                track_info[1],
                "Main Mix",
                "Full",
                trackLength
            ]
            sec60 = [
                track_info[1],
                "60 Sec Edit",
                "60",
                "1:00"
            ]
            sec30 = [
                track_info[1],
                "30 Sec Edit",
                "30",
                "0:30"
            ]
            short = [
                track_info[1],
                "Bumper Edit",
                "Short",
                "0:15"
            ]
            versionWriter.writerow(full)
            versionWriter.writerow(sec60)
            versionWriter.writerow(sec30)
            versionWriter.writerow(short)
            for version in trackProperties["Song Versions"]["relation"]:
                version_properties = ReadPageProperties(version["id"])
                version_info = [
                    track_info[1],
                    version_properties["Mixout"]["rich_text"][0]["plain_text"] if version_properties["Mixout"]["rich_text"] else "",
                    version_properties["Version"]["select"]["name"],
                    trackLength
                ]
                versionWriter.writerow(version_info)
                console.Log(f"Processing version: {version_info[2]} for track: {track_info[0]}")
    albumsFile.close()
    tracksFile.close()
    versionsFile.close()
    moodsFile.close()
    genresFile.close()
    miscFile.close()
    composersFile.close()
    contentProvidersFile.close()
    console.Log("Done!")


def ShowError(message: str, parent=None) -> None:
    """Show an error message box with the given message."""
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setWindowTitle("Error")
    msg.setText(message)
    msg.exec()

def AddNewTab(tabName: str, contentFunc=None) -> tuple:
    """Add a new tab to the main window, or switch to it if it exists."""
    # Check if tab already exists
    for i in range(tabs.count()):
        if tabs.tabText(i) == tabName:
            tabs.setCurrentIndex(i)
            return tabs.widget(i), tabs.widget(i).layout()
    # If not, create a new tab
    newTab = QWidget()
    newTabLayout = QVBoxLayout()
    newTab.setLayout(newTabLayout)
    tabs.addTab(newTab, tabName)
    tabs.setCurrentWidget(newTab)

    # Add custom content if provided
    if contentFunc:
        contentFunc(newTabLayout)

    return newTab, newTabLayout

def CheckForUpdates(parent=None):
    """Check GitHub Releases for a new version and prompt to download."""
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            latest_version = data["tag_name"].lstrip("v")
            if latest_version > APP_VERSION:
                msg = QMessageBox(parent)
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle("Update Available")
                msg.setText(f"A new version ({latest_version}) is available!\n\nWould you like to download it?")
                msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if msg.exec() == QMessageBox.StandardButton.Yes:
                    webbrowser.open(data["html_url"])
        # else: ignore errors silently
    except Exception as e:
        print(f"Update check failed: {e}")

def CreateLauncherButton(text: str, gridLayout: QGridLayout, row: int, col: int, callback=None) -> QPushButton:
    """Create a large launcher button for the main grid."""
    btn = QPushButton(text)
    btn.setMinimumSize(120, 120)
    btn.setStyleSheet("font-size: 18px; font-weight: bold;")
    if callback:
        btn.clicked.connect(callback)
    gridLayout.addWidget(btn, row, col)
    return btn


if __name__ == "__main__":
    """Main entry point for the FNB Helper application."""
    app = QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle("FNB Helper")
    window.resize(700, 400)

    layout = QVBoxLayout()
    global tabs
    tabs = QTabWidget()
    tab1, tab1Layout = AddNewTab("Launcher")

    gridLayout = QGridLayout()
    
    btn1 = CreateLauncherButton("Harvest Processer", gridLayout, 0, 0, lambda: AddNewTab("Harvest Processer", CreateHarevestLayout))
    btn2 = CreateLauncherButton("Version Adder", gridLayout, 0, 1, lambda: AddNewTab("Version Adder", CreateVersionsLayout))
    btn3 = CreateLauncherButton("Filemaker Importer", gridLayout, 0, 2, lambda: AddNewTab("Filemaker Importer", CreateImportLayout))

    tab1Layout.addLayout(gridLayout)

    layout.addWidget(tabs)
    window.setLayout(layout)
    window.show()

    CheckForUpdates(window)

    sys.exit(app.exec())