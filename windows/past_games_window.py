import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QAbstractItemView, QHeaderView, QLineEdit, QProgressDialog, QApplication
)
from PyQt6.QtCore import Qt
from nhlpy import NHLClient
from .game_details_window import GameDetailsWindow


class PastGamesWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Past NHL Games")
        self.resize(800, 600)

        self.client = NHLClient()
        self.games = []

        # Show a small loading dialog while we fetch a full season of games,
        # so the user knows the window is working and not frozen.
        self.fetch_past_games_with_progress()
        self.original_games = list(self.games)

        self.current_sort_col = -1
        self.current_sort_order = 0

        self.init_ui()

    def fetch_past_games_with_progress(self):
        today = datetime.date.today()
        # Assume season starts on October 1st of the current or previous year
        if today.month >= 10:
            start_date = datetime.date(today.year, 10, 1)
        else:
            start_date = datetime.date(today.year - 1, 10, 1)

        total_days = (today - start_date).days

        progress = QProgressDialog("Loading past games...", "Cancel", 0, total_days, self)
        progress.setWindowTitle("Please wait")
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setAutoClose(True)
        progress.setAutoReset(True)
        # Give it a subtle "terminal" look by using a monospace font
        progress.setStyleSheet("QLabel { font-family: Consolas, 'Courier New', monospace; }")

        current_date = start_date
        day_index = 0
        spinner = "|/-\\"
        spinner_index = 0

        while current_date < today:
            if progress.wasCanceled():
                break

            day_str = current_date.isoformat()
            spin_char = spinner[spinner_index % len(spinner)]
            progress.setLabelText(f"{spin_char} Loading games for {day_str}...")
            progress.setValue(day_index)
            spinner_index += 1

            # Allow the UI (including the loading dialog) to repaint
            QApplication.processEvents()

            try:
                sched = self.client.schedule.daily_schedule(date=day_str)
                self.games.extend(sched.get("games", []))
            except Exception:
                pass  # Skip if no games or error

            current_date += datetime.timedelta(days=1)
            day_index += 1

        progress.setValue(total_days)

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
        self.table.setColumnCount(6)
        headers = ["Date", "Matchup", "Score", "Time (EST)", "Venue", "TV"]

        for col, text in enumerate(headers):
            self.table.setHorizontalHeaderItem(col, QTableWidgetItem(text))

        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.sectionClicked.connect(self.handle_header_click)

        # Allow opening matchup details from past games
        self.table.itemClicked.connect(self.handle_item_click)

        self.populate_table()
        self.update_sort_indicator()

        layout.addWidget(self.table)

    def populate_table(self):
        self.table.setRowCount(len(self.games))

        for row, game in enumerate(self.games):
            away = game.get("awayTeam", {}).get("abbrev", "")
            home = game.get("homeTeam", {}).get("abbrev", "")
            matchup = f"{away} @ {home}"
            away_score = game.get("awayTeam", {}).get("score", "")
            home_score = game.get("homeTeam", {}).get("score", "")
            score_str = f"{away_score} - {home_score}"

            # Add OT or SO if applicable
            period_type = game.get("gameOutcome", {}).get("lastPeriodType", "")
            if period_type == "OT":
                score_str += " (OT)"
            elif period_type == "SO":
                score_str += " (SO)"

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
                QTableWidgetItem(score_str),
                QTableWidgetItem(time_str),
                QTableWidgetItem(venue),
                QTableWidgetItem(tv_str),
            ]

            for col, item in enumerate(items):
                self.table.setItem(row, col, item)

            matchup_item = items[1]
            game_id = game.get("id", "")
            matchup_item.setData(Qt.ItemDataRole.UserRole, game_id)
            matchup_item.setData(Qt.ItemDataRole.UserRole + 1, row)

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
            lambda g: (g.get('awayTeam', {}).get('score', 0), g.get('homeTeam', {}).get('score', 0)),  # Score (sort by away then home score)
            lambda g: datetime.datetime.fromisoformat(g.get("startTimeUTC", "").replace("Z", "+00:00")) if g.get("startTimeUTC") else datetime.datetime.min,  # Time (same as date for precision)
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

    def handle_item_click(self, item):
        """Open matchup details when matchup column is clicked."""
        if item.column() == 1:
            game_id = item.data(Qt.ItemDataRole.UserRole)
            row = item.data(Qt.ItemDataRole.UserRole + 1)
            if row is not None and 0 <= row < len(self.games):
                self.open_game_details(self.games[row])

    def open_game_details(self, game):
        """Show the game details window for a past matchup."""
        self.game_details_window = GameDetailsWindow(game, self.client)
        self.game_details_window.show()

