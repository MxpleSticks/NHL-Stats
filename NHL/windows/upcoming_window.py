import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QAbstractItemView, QHeaderView, QPushButton, QLineEdit, QHBoxLayout,
    QProgressDialog, QApplication
)
from PyQt6.QtCore import Qt
from nhlpy import NHLClient
from delegates import HighlightDelegate
from .past_games_window import PastGamesWindow
from .game_details_window import GameDetailsWindow


class UpcomingWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Upcoming NHL Games")
        self.resize(800, 600)

        self.client = NHLClient()
        self.games = []
        self.fetch_upcoming_games_with_progress()
        self.original_games = list(self.games)

        self.current_sort_col = -1
        self.current_sort_order = 0

        self.init_ui()

    def fetch_upcoming_games_with_progress(self):
        today = datetime.date.today()

        dialog = QProgressDialog("Loading upcoming games...", None, 0, 0, self)
        dialog.setWindowTitle("Please wait")
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        dialog.setAutoClose(True)
        dialog.setAutoReset(True)
        dialog.setMinimumDuration(0)
        dialog.setStyleSheet("QLabel { font-family: Consolas, 'Courier New', monospace; }")

        dialog.show()
        QApplication.processEvents()

        spinner = "|/-\\"
        spinner_index = 0

        for i in range(7):
            day = today + datetime.timedelta(days=i)
            day_str = day.isoformat()
            spin_char = spinner[spinner_index % len(spinner)]
            dialog.setLabelText(f"{spin_char} Loading games for {day_str}...")
            QApplication.processEvents()
            spinner_index += 1
            try:
                sched = self.client.schedule.daily_schedule(date=day_str)
                self.games.extend(sched.get("games", []))
            except Exception:
                pass  # Skip if no games or error

        dialog.close()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search...")
        self.search_bar.textChanged.connect(self.filter_table)
        layout.addWidget(self.search_bar)

        self.table = QTableWidget()
        self.table.setShowGrid(False)
        self.table.setColumnCount(5)
        headers = ["Date", "Matchup", "Time (EST)", "Venue", "TV"]

        for col, text in enumerate(headers):
            self.table.setHorizontalHeaderItem(col, QTableWidgetItem(text))

        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.sectionClicked.connect(self.handle_header_click)

        self.populate_table()
        self.update_sort_indicator()
        
        # Connect item clicked signal to handle matchup clicks
        self.table.itemClicked.connect(self.handle_item_click)

        layout.addWidget(self.table)

        # Button layout for predictions
        button_layout = QHBoxLayout()

        # Add button for predicted goalies
        self.goalies_button = QPushButton("View Predicted Goalies")
        self.goalies_button.clicked.connect(self.open_goalies_window)
        button_layout.addWidget(self.goalies_button)

        # Add button for predicted lineups
        self.lineups_button = QPushButton("View Predicted Lineups")
        self.lineups_button.clicked.connect(self.open_lineups_window)
        button_layout.addWidget(self.lineups_button)

        # Add button for past games
        self.past_button = QPushButton("View Past Games")
        self.past_button.clicked.connect(self.open_past_window)
        button_layout.addWidget(self.past_button)

        layout.addLayout(button_layout)

    def open_goalies_window(self):
        from .web_windows import GoaliesWindow
        self.goalies_window = GoaliesWindow()
        self.goalies_window.show()

    def open_lineups_window(self):
        from .web_windows import LineupsWindow
        self.lineups_window = LineupsWindow()
        self.lineups_window.show()

    def open_past_window(self):
        self.past_window = PastGamesWindow()
        self.past_window.show()
    
    def handle_item_click(self, item):
        """Handle clicks on matchup column"""
        if item.column() == 1:  # Matchup column
            game_id = item.data(Qt.ItemDataRole.UserRole)
            row = item.data(Qt.ItemDataRole.UserRole + 1)
            if game_id and row is not None and row < len(self.games):
                game = self.games[row]
                self.open_game_details(game)
    
    def open_game_details(self, game):
        """Open game details window"""
        self.game_details_window = GameDetailsWindow(game, self.client)
        self.game_details_window.show()

    def populate_table(self):
        self.table.setRowCount(len(self.games))
        today_str = datetime.date.today().isoformat()
        highlight_rows = set()

        for row, game in enumerate(self.games):
            away = game.get("awayTeam", {}).get("abbrev", "")
            home = game.get("homeTeam", {}).get("abbrev", "")
            matchup = f"{away} @ {home}"
            start_time = game.get("startTimeUTC", "")
            venue = game.get("venue", {}).get("default", "")
            tv_broadcasts = game.get("tvBroadcasts", [])
            tv_str = ", ".join(b.get("network", "") for b in tv_broadcasts) if tv_broadcasts else ""

            # Convert time to EST and 12-hour AM/PM, then extract date from EST
            time_str = ""
            game_date = ""
            if start_time:
                utc_time = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                est_time = utc_time - datetime.timedelta(hours=5)
                time_str = est_time.strftime("%I:%M %p")
                game_date = est_time.date().isoformat()

            items = [
                QTableWidgetItem(game_date),
                QTableWidgetItem(matchup),
                QTableWidgetItem(time_str),
                QTableWidgetItem(venue),
                QTableWidgetItem(tv_str),
            ]

            for col, item in enumerate(items):
                self.table.setItem(row, col, item)
            
            # Store game ID in matchup item for click handling
            matchup_item = items[1]  # Matchup is column 1
            game_id = game.get("id", "")
            matchup_item.setData(Qt.ItemDataRole.UserRole, game_id)
            matchup_item.setData(Qt.ItemDataRole.UserRole + 1, row)  # Store row index

            if game_date == today_str:
                highlight_rows.add(row)

        if highlight_rows:
            delegate = HighlightDelegate(highlight_rows, self.table)
            self.table.setItemDelegate(delegate)

    def filter_table(self, text):
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)

    def get_sort_key(self, col):
        keys = [
            lambda g: datetime.datetime.fromisoformat(g.get("startTimeUTC", "").replace("Z", "+00:00")) if g.get("startTimeUTC") else datetime.datetime.min,  # Date
            lambda g: f"{g.get('awayTeam', {}).get('abbrev', '')} @ {g.get('homeTeam', {}).get('abbrev', '')}",  # Matchup
            lambda g: datetime.datetime.fromisoformat(g.get("startTimeUTC", "").replace("Z", "+00:00")) if g.get("startTimeUTC") else datetime.datetime.min,  # Time
            lambda g: g.get("venue", {}).get("default", ""),  # Venue
            lambda g: ", ".join(b.get("network", "") for b in g.get("tvBroadcasts", [])),  # TV
        ]
        return keys[col]

    def handle_header_click(self, col):
        if self.current_sort_col == col:
            self.current_sort_order = (self.current_sort_order + 1) % 3
        else:
            self.current_sort_col = col
            self.current_sort_order = 1  # start ascending

        # Actually sort the data
        if self.current_sort_order == 0:
            self.games = list(self.original_games)
        else:
            key = self.get_sort_key(col)
            reverse = (self.current_sort_order == 2)
            self.games = sorted(self.original_games, key=key, reverse=reverse)

        self.populate_table()
        self.update_sort_indicator()
        self.filter_table(self.search_bar.text())

    def update_sort_indicator(self):
        header = self.table.horizontalHeader()
        if self.current_sort_order == 0:
            header.setSortIndicatorShown(False)
        else:
            order = Qt.SortOrder.AscendingOrder if self.current_sort_order == 1 else Qt.SortOrder.DescendingOrder
            header.setSortIndicator(self.current_sort_col, order)
            header.setSortIndicatorShown(True)

