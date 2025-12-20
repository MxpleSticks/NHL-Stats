import datetime
import json
import os
from PyQt6.QtWidgets import (
    QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QAbstractItemView, QHeaderView, QProgressDialog, QApplication
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from nhlpy import NHLClient
from .game_details_window import GameDetailsWindow


class TodaysGamesWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Today's NHL Games")
        self.resize(800, 600)

        self.client = NHLClient()
        self.games = []

        # Quick loading dialog so the user sees feedback if today's
        # schedule takes a moment to load.
        self.fetch_todays_games_with_loading()
        
        # Load favorite teams
        self.favorites_file = os.path.join(os.path.expanduser("~"), ".nhl_favorites.json")
        self.favorite_teams = set()
        self.load_favorites()
        
        # Rainbow animation for favorite teams
        self.rainbow_items = []
        self.rainbow_offset = 0
        self.rainbow_timer = QTimer()
        self.rainbow_timer.timeout.connect(self.update_rainbow_colors)
        self.rainbow_timer.start(50)

        self.init_ui()
    
    def load_favorites(self):
        """Load favorite teams from file"""
        try:
            if os.path.exists(self.favorites_file):
                with open(self.favorites_file, 'r') as f:
                    self.favorite_teams = set(json.load(f))
        except Exception:
            self.favorite_teams = set()
    
    def get_rainbow_color(self, offset):
        """Generate a rainbow color based on offset (0-360 degrees)"""
        hue = (offset % 360) / 360.0
        saturation = 1.0
        value = 1.0
        
        c = value * saturation
        x = c * (1 - abs((hue * 6) % 2 - 1))
        m = value - c
        
        if hue < 1/6:
            r, g, b = c, x, 0
        elif hue < 2/6:
            r, g, b = x, c, 0
        elif hue < 3/6:
            r, g, b = 0, c, x
        elif hue < 4/6:
            r, g, b = 0, x, c
        elif hue < 5/6:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
        
        return QColor(int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))
    
    def update_rainbow_colors(self):
        """Update rainbow colors for all items in rainbow_items"""
        self.rainbow_offset = (self.rainbow_offset + 2) % 360
        for idx, (item, row, col) in enumerate(self.rainbow_items):
            if item and self.table.item(row, col) == item:
                # Add a phase offset based on item index for flowing effect
                phase_offset = (idx * 30) % 360  # Each item offset by 30 degrees
                color = self.get_rainbow_color(self.rainbow_offset + phase_offset)
                item.setForeground(color)

    def fetch_todays_games_with_loading(self):
        today = datetime.date.today()
        day_str = today.isoformat()

        dialog = QProgressDialog("Loading today's games...", None, 0, 0, self)
        dialog.setWindowTitle("Please wait")
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        dialog.setAutoClose(True)
        dialog.setAutoReset(True)
        dialog.setMinimumDuration(0)

        dialog.show()
        QApplication.processEvents()

        try:
            sched = self.client.schedule.daily_schedule(date=day_str)
            self.games = sched.get("games", [])
        except Exception:
            self.games = []

        dialog.close()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setShowGrid(False)
        self.table.setColumnCount(6)
        headers = ["Time", "Matchup", "Score", "Status", "Venue", "TV"]

        for col, text in enumerate(headers):
            self.table.setHorizontalHeaderItem(col, QTableWidgetItem(text))

        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.populate_table()
        
        # Connect item clicked signal to handle matchup clicks
        self.table.itemClicked.connect(self.handle_item_click)

        layout.addWidget(self.table)
    
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

        for row, game in enumerate(self.games):
            away = game.get("awayTeam", {}).get("abbrev", "")
            home = game.get("homeTeam", {}).get("abbrev", "")
            matchup = f"{away} @ {home}"
            
            # Get scores
            away_score = game.get("awayTeam", {}).get("score", 0)
            home_score = game.get("homeTeam", {}).get("score", 0)
            
            # Determine game status
            game_state = game.get("gameState", "")
            game_outcome = game.get("gameOutcome", {})
            
            # Check if game has meaningful scores (not 0 or empty)
            # Scores of 0 might be default values for games that haven't started
            has_scores = (
                (away_score is not None and away_score != "" and away_score != 0) or 
                (home_score is not None and home_score != "" and home_score != 0)
            )
            has_outcome = bool(game_outcome)
            
            # Format score based on game state
            # Prioritize game_state over scores since scores might be default values
            if game_state == "LIVE":
                score_str = f"{away_score} - {home_score}"
                period_descriptor = game.get("periodDescriptor", {}) or {}

                # Try several ways to determine the current period, since the API
                # structure can vary and sometimes returns 0 here.
                period = game.get("period")
                if not period:
                    # Look for a more explicit period number in the descriptor
                    for key in ("number", "periodNumber", "period"):
                        value = period_descriptor.get(key)
                        if isinstance(value, int) and value > 0:
                            period = value
                            break

                # As a last resort, avoid showing "Period 0" while live
                if not period:
                    period = 1

                period_type = period_descriptor.get("periodType", "")
                if period_type == "OT":
                    status_str = f"OT {period}"
                elif period_type == "SO":
                    status_str = "SO"
                else:
                    # Fallbacks so we never display "Period 0"
                    if period_type and period:
                        status_str = f"{period_type} {period}"
                    elif period:
                        status_str = f"Period {period}"
                    else:
                        status_str = "In Progress"
            elif game_state == "FINAL" or game_state == "OFFICIAL" or has_outcome:
                # Game is finished - show final score
                score_str = f"{away_score} - {home_score}"
                period_type = game_outcome.get("lastPeriodType", "") if game_outcome else ""
                if period_type == "OT":
                    score_str += " (OT)"
                    status_str = "Final/OT"
                elif period_type == "SO":
                    score_str += " (SO)"
                    status_str = "Final/SO"
                else:
                    status_str = "Final"
            else:
                # Game hasn't started or is in preview state - show as upcoming
                # Don't rely on scores since they might be default/placeholder values
                score_str = "VS"
                status_str = "Upcoming"

            start_time = game.get("startTimeUTC", "")
            venue = game.get("venue", {}).get("default", "")
            tv_broadcasts = game.get("tvBroadcasts", [])
            tv_str = ", ".join(b.get("network", "") for b in tv_broadcasts) if tv_broadcasts else ""

            # Convert time to EST and 12-hour AM/PM
            time_str = ""
            if start_time:
                utc_time = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                est_time = utc_time - datetime.timedelta(hours=5)
                time_str = est_time.strftime("%I:%M %p")

            items = [
                QTableWidgetItem(time_str),
                QTableWidgetItem(matchup),
                QTableWidgetItem(score_str),
                QTableWidgetItem(status_str),
                QTableWidgetItem(venue),
                QTableWidgetItem(tv_str),
            ]

            # Color code games based on status
            is_final = game_state == "FINAL" or game_state == "OFFICIAL" or has_outcome or (has_scores and game_state == "OFF")
            is_favorite = away in self.favorite_teams or home in self.favorite_teams
            
            # Check if favorite team won
            favorite_won = False
            if is_final and is_favorite and has_scores:
                # Ensure scores are numeric for comparison
                try:
                    away_score_num = int(away_score) if away_score is not None and away_score != "" else 0
                    home_score_num = int(home_score) if home_score is not None and home_score != "" else 0
                    away_is_favorite = away in self.favorite_teams
                    home_is_favorite = home in self.favorite_teams
                    # Check if favorite team won
                    if away_is_favorite and away_score_num > home_score_num:
                        favorite_won = True
                    elif home_is_favorite and home_score_num > away_score_num:
                        favorite_won = True
                except (ValueError, TypeError):
                    # If scores can't be converted to int, skip rainbow effect
                    pass
            
            if is_final:
                # Final games - use green, or rainbow if favorite team won
                if favorite_won:
                    # Add all items to rainbow animation
                    for col_idx, item in enumerate(items):
                        self.rainbow_items.append((item, row, col_idx))
                else:
                    # Regular green for all final games (favorites that lost or non-favorites)
                    for item in items:
                        item.setForeground(QColor("green"))
            # Ongoing and upcoming games stay white (default color)

            for col, item in enumerate(items):
                self.table.setItem(row, col, item)
            
            # Store game ID in matchup item for click handling
            matchup_item = items[1]  # Matchup is column 1
            game_id = game.get("id", "")
            matchup_item.setData(Qt.ItemDataRole.UserRole, game_id)
            matchup_item.setData(Qt.ItemDataRole.UserRole + 1, row)  # Store row index

