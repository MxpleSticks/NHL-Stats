import datetime
import json
import os
import math
from PyQt6.QtWidgets import (
    QLabel, QMainWindow, QScrollArea, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QAbstractItemView, QHeaderView, QPushButton, QHBoxLayout
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor
from nhlpy import NHLClient
from delegates import FavoriteDelegate
from .web_windows import TeamLinesWindow, PlayoffWindow
from .games_windows import UpcomingWindow, TodaysGamesWindow
from .comparison_window import ComparisonWindow
from .team_matchup_window import TeamMatchupWindow
from .game_details_window import GameDetailsWindow
from .prediction_window import PredictionWindow


class ClickableBannerLabel(QLabel):
    """Clickable label used in the top scrolling banner."""
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NHL Standings")
        self.resize(1000, 700)

        self.client = NHLClient()
        current_date = datetime.date.today().isoformat()
        self.standings = self.client.standings.league_standings(date=current_date)["standings"]
        self.original_standings = list(self.standings)

        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        try:
            yesterday_data = self.client.standings.league_standings(date=yesterday)["standings"]
            self.prev_ranks = {team["teamAbbrev"]["default"]: team["leagueSequence"] for team in yesterday_data}
        except Exception:
            self.prev_ranks = {}  # If fetch fails, no arrows

        # Get ranks and stats from 2 days ago for comparison (default)
        two_days_ago = (datetime.date.today() - datetime.timedelta(days=2)).isoformat()
        try:
            two_days_data = self.client.standings.league_standings(date=two_days_ago)["standings"]
            self.two_days_ago_ranks = {team["teamAbbrev"]["default"]: team["leagueSequence"] for team in two_days_data}
            # Store full 2 days ago data for stat comparisons
            self.two_days_ago_stats = {team["teamAbbrev"]["default"]: team for team in two_days_data}
        except Exception:
            self.two_days_ago_ranks = {}  # If fetch fails, no comparison
            self.two_days_ago_stats = {}  # If fetch fails, no stat comparisons

        self.current_sort_col = -1      # -1 = original order
        self.current_sort_order = 0     # 0=original, 1=asc, 2=desc
        self.advanced_mode = False
        self.favorite_teams = set()  # Track favorite teams by abbreviation
        self.favorites_file = os.path.join(os.path.expanduser("~"), ".nhl_favorites.json")
        self.load_favorites()
        self.comparison_date = None  # For custom date comparison (ranks dict)
        self.comparison_stats = None  # For custom date comparison (full stats dict)
        self.team_schedule_cache = {}
        self.team_last_game_cache = {}
        self.last_game_col = -1
        self.playoff_col = -1
        self.basic_column_count = 0

        self.banner_games_data = []
        self.banner_scroll_timer = QTimer()
        self.banner_scroll_timer.timeout.connect(self.advance_banner)
        self.scroll_speed = 1
        
        # Rainbow animation for favorite teams
        self.rainbow_items = []  # List of (item, row, col) tuples for rainbow animation
        self.rainbow_banner_labels = []  # List of banner labels that should have rainbow effect
        self.rainbow_offset = 0  # Current offset in rainbow cycle
        self.rainbow_timer = QTimer()
        self.rainbow_timer.timeout.connect(self.update_rainbow_colors)
        self.rainbow_timer.start(50)  # Update every 50ms for smooth animation

        self.init_ui()
        self.banner_scroll_timer.start(30)

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.banner_scroll = QScrollArea()
        self.banner_scroll.setFixedHeight(20)
        self.banner_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.banner_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.banner_scroll.setWidgetResizable(False)
        self.banner_content = QWidget()
        self.banner_layout = QHBoxLayout(self.banner_content)
        self.banner_layout.setContentsMargins(10, 0, 10, 0)
        self.banner_layout.setSpacing(40)
        self.banner_scroll.setWidget(self.banner_content)
        self.banner_scroll.setStyleSheet("background: transparent; border: none;")
        self.banner_content.setStyleSheet("background: transparent;")
        layout.addWidget(self.banner_scroll)

        self.refresh_banner(force_fetch=False)

        # === Table setup ===
        self.table = QTableWidget()
        self.table.setShowGrid(False)

        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.sectionClicked.connect(self.handle_header_click)

        # Connect item clicked signal
        self.table.itemClicked.connect(self.handle_item_click)

        self.update_table_columns()
        self.populate_table()
        self.update_sort_indicator()

        layout.addWidget(self.table)

        # Button layout
        button_layout = QHBoxLayout()

        # Add button for playoff probabilities (left)
        self.playoff_button = QPushButton("View Playoff Probabilities")
        self.playoff_button.clicked.connect(self.open_playoff_window)
        button_layout.addWidget(self.playoff_button)

        # Add button for today's games
        self.todays_button = QPushButton("Today's Games Summary")
        self.todays_button.clicked.connect(self.open_todays_games)
        button_layout.addWidget(self.todays_button)

        # Add button for upcoming games (right)
        self.button = QPushButton("View Upcoming Games")
        self.button.clicked.connect(self.open_upcoming_games)
        button_layout.addWidget(self.button)

        self.matchup_button = QPushButton("Team Matchup")
        self.matchup_button.clicked.connect(self.open_team_matchup)
        button_layout.addWidget(self.matchup_button)

        self.prediction_button = QPushButton("Daily Picks")
        self.prediction_button.clicked.connect(self.open_prediction_window)
        button_layout.addWidget(self.prediction_button)

        # Add toggle advanced mode button
        self.advanced_button = QPushButton("Enable Advanced Mode")
        self.advanced_button.clicked.connect(self.toggle_advanced_mode)
        self.advanced_button.setMaximumWidth(150)
        font = self.advanced_button.font()
        font.setPointSize(8)
        self.advanced_button.setFont(font)
        button_layout.addWidget(self.advanced_button)

        # Add compare button
        self.compare_button = QPushButton("Compare")
        self.compare_button.clicked.connect(self.open_comparison_window)
        self.compare_button.setMaximumWidth(100)
        font = self.compare_button.font()
        font.setPointSize(8)
        self.compare_button.setFont(font)
        button_layout.addWidget(self.compare_button)

        layout.addLayout(button_layout)

    def toggle_advanced_mode(self):
        self.advanced_mode = not self.advanced_mode
        self.advanced_button.setText("Disable Advanced Mode" if self.advanced_mode else "Enable Advanced Mode")
        self.update_table_columns()
        # Don't refresh the top game banner when just toggling column view,
        # so the scroller stays visible and keeps its current content.
        self.populate_table(refresh_banner=False)
        self.update_sort_indicator()

    def load_favorites(self):
        """Load favorite teams from file"""
        try:
            if os.path.exists(self.favorites_file):
                with open(self.favorites_file, 'r') as f:
                    self.favorite_teams = set(json.load(f))
        except Exception:
            self.favorite_teams = set()

    def save_favorites(self):
        """Save favorite teams to file"""
        try:
            with open(self.favorites_file, 'w') as f:
                json.dump(list(self.favorite_teams), f)
        except Exception:
            pass

    def closeEvent(self, event):
        """Save favorites when closing the app"""
        self.save_favorites()
        event.accept()

    def refresh_banner(self, force_fetch=False):
        """Refresh the rolling ticker with today's matchups."""
        if force_fetch or not self.banner_games_data:
            self.banner_games_data = self.fetch_today_games()
        self.render_banner()

    def fetch_today_games(self):
        today = datetime.date.today().isoformat()
        try:
            sched = self.client.schedule.daily_schedule(date=today)
            return sched.get("games", [])
        except Exception:
            return []

    def render_banner(self):
        if not hasattr(self, "banner_layout"):
            return

        while self.banner_layout.count():
            item = self.banner_layout.takeAt(0)
            if not item:
                continue
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Clear rainbow banner labels list when re-rendering
        self.rainbow_banner_labels = []

        entries = []
        for game in self.banner_games_data:
            away = game.get("awayTeam", {}).get("abbrev", "")
            home = game.get("homeTeam", {}).get("abbrev", "")
            time_str = self.format_time_for_banner(game.get("startTimeUTC", ""))

            # Determine score and status for banner text
            away_score = game.get("awayTeam", {}).get("score", 0)
            home_score = game.get("homeTeam", {}).get("score", 0)
            game_state = game.get("gameState", "")
            game_outcome = game.get("gameOutcome", {})

            has_scores = (
                away_score is not None and away_score != "" or
                home_score is not None and home_score != ""
            )
            has_outcome = bool(game_outcome)

            score_str = f"{away_score} - {home_score}" if has_scores else ""

            # Build display text:
            # - LIVE games: show matchup + live score
            # - FINAL games: show matchup + final score
            # - Upcoming: show matchup + start time
            if game_state == "LIVE":
                text = f"{away} vs {home} {score_str}"
            elif game_state in ("FINAL", "OFFICIAL") or has_outcome or (has_scores and game_state == "OFF"):
                text = f"{away} vs {home} {score_str}"
            else:
                text = f"{away} vs {home} {time_str}"

            is_favorite = away in self.favorite_teams or home in self.favorite_teams
            is_live = game_state == "LIVE"
            
            # Check if game is finished and favorite team won
            is_finished = game_state in ("FINAL", "OFFICIAL") or has_outcome or (has_scores and game_state == "OFF")
            favorite_won = False
            if is_finished and is_favorite and has_scores:
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
            
            entries.append((text, is_favorite, is_live, game, favorite_won))

        if not entries:
            # Show a scrolling message when no games are scheduled today
            message = "No games scheduled today"
            entries = [(message, False, False, None, False)]

        repeat = 10
        for _ in range(repeat):
            for text, is_favorite, is_live, game, favorite_won in entries:
                label = ClickableBannerLabel(text)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                # Live games: green text, favorites bold; others: white text, favorites bold
                # If favorite won, don't set color here - let rainbow animation handle it
                if favorite_won:
                    # Will be handled by rainbow animation
                    style = "font-size: 12px; font-weight: bold;"
                elif is_live:
                    style = "color: #0f0; font-size: 12px;"
                else:
                    style = "color: #fff; font-size: 12px;"
                if is_favorite and not favorite_won:
                    style += " font-weight: bold;"
                label.setStyleSheet(style)
                # Store game data on the label and connect click to open details
                if game:
                    label.game = game
                    label.clicked.connect(lambda g=game: self.open_banner_game_details(g))
                self.banner_layout.addWidget(label)
                
                # Add to rainbow list if favorite team won
                if favorite_won:
                    self.rainbow_banner_labels.append(label)

        self.banner_content.adjustSize()

    def format_time_for_banner(self, start_time):
        if not start_time:
            return "TBD"
        try:
            utc_time = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            est_time = utc_time - datetime.timedelta(hours=5)
            return est_time.strftime("%I:%M %p").lstrip("0")
        except Exception:
            return "TBD"

    def open_banner_game_details(self, game):
        """Open the detailed game window when a banner entry is clicked."""
        try:
            self.banner_game_details_window = GameDetailsWindow(game, self.client)
            self.banner_game_details_window.show()
        except Exception as e:
            print(f"Failed to open game details from banner: {e}")

    def advance_banner(self):
        if not hasattr(self, "banner_scroll"):
            return
        bar = self.banner_scroll.horizontalScrollBar()
        if bar.maximum() <= 0:
            return
        next_value = bar.value() + self.scroll_speed
        if next_value >= bar.maximum():
            next_value = 0
        bar.setValue(next_value)

    def update_table_columns(self):
        basic_headers = ["Rank", "Team", "GP", "W", "L", "OT", "Pts", "ROW", "P%", "GF", "GA", "DIFF", "HOME", "ROAD", "L10", "STREAK", "Last", "Playoffs"]
        advanced_headers = ["RW", "SOW", "SOL", "Conf", "Div", "Wild"]
        headers = basic_headers + advanced_headers if self.advanced_mode else basic_headers

        basic_tooltips = [
            "League Rank", "Team Abbreviation", "Games Played", "Wins", "Losses",
            "Overtime Losses", "Points", "Regulation + OT Wins", "Point Percentage",
            "Goals For", "Goals Against", "Goal Differential",
            "Home Record (W-L-OT)", "Road Record (W-L-OT)", "Last 10 Games (W-L-OT)", "Current Streak",
            "Result of most recent game (click to open details)",
            "Playoff Status (if season ended today)"
        ]
        advanced_tooltips = [
            "Regulation Wins", "Shootout Wins", "Shootout Losses",
            "Conference Rank", "Division Rank", "Wildcard Rank"
        ]
        tooltips = basic_tooltips + advanced_tooltips if self.advanced_mode else basic_tooltips

        self.basic_column_count = len(basic_headers)
        self.last_game_col = basic_headers.index("Last") if "Last" in basic_headers else -1
        self.playoff_col = basic_headers.index("Playoffs") if "Playoffs" in basic_headers else -1

        self.table.setColumnCount(len(headers))
        for col, (text, tip) in enumerate(zip(headers, tooltips)):
            item = QTableWidgetItem(text)
            item.setToolTip(tip)
            self.table.setHorizontalHeaderItem(col, item)

        # Enable tooltips for header
        self.table.horizontalHeader().setToolTip("")

    def handle_item_click(self, item):
        if item.column() == 0:  # Rank column - toggle favorite
            abbrev = self.table.item(item.row(), 1).text()
            if abbrev in self.favorite_teams:
                self.favorite_teams.remove(abbrev)
            else:
                self.favorite_teams.add(abbrev)
            self.populate_table(refresh_banner=False)
            self.update_sort_indicator()
        elif item.column() == 1:  # Team column - view players
            full_name = item.toolTip().lower()
            full_name = full_name.replace("é", "e").replace(".", "")
            full_name = full_name.replace(" ", "-")
            url = f"https://www.dailyfaceoff.com/teams/{full_name}/line-combinations"
            print(f"Opening URL: {url}")
            self.team_lines_window = TeamLinesWindow(url)
            self.team_lines_window.show()
        elif self.last_game_col != -1 and item.column() == self.last_game_col:
            team_item = self.table.item(item.row(), 1)
            if team_item:
                abbrev = team_item.text()
                self.open_team_last_game(abbrev)

    def open_todays_games(self):
        self.todays_window = TodaysGamesWindow()
        self.todays_window.show()

    def open_upcoming_games(self):
        self.upcoming_window = UpcomingWindow()
        self.upcoming_window.show()

    def open_team_matchup(self):
        self.team_matchup_window = TeamMatchupWindow(self)
        self.team_matchup_window.show()

    def open_prediction_window(self):
        self.prediction_window = PredictionWindow()
        self.prediction_window.show()

    def open_comparison_window(self):
        dialog = ComparisonWindow(self)
        dialog.exec()

    def open_team_last_game(self, team_abbrev):
        """Open the most recent completed game for the provided team."""
        if not team_abbrev:
            return
        result, game = self.get_team_last_game_data(team_abbrev)
        if not game:
            print(f"No completed games found for {team_abbrev}")
            return
        try:
            self.last_game_details_window = GameDetailsWindow(game, self.client)
            self.last_game_details_window.show()
        except Exception as e:
            print(f"Failed to open last game for {team_abbrev}: {e}")

    def get_last_result_letter(self, team):
        """Return the last game result letter for display/sorting."""
        if not team:
            return "-"
        streak_code = team.get("streakCode", "")
        if streak_code in ("W", "L"):
            return streak_code
        abbrev = team.get("teamAbbrev", {}).get("default", "")
        if not abbrev:
            return "-"
        result, _ = self.get_team_last_game_data(abbrev)
        return result if result in ("W", "L") else "-"

    def get_team_last_game_data(self, team_abbrev):
        """Return the most recent completed game (and result) for a team."""
        if team_abbrev in self.team_last_game_cache:
            return self.team_last_game_cache[team_abbrev]

        games = self.get_team_schedule(team_abbrev)
        last_game = None
        for game in sorted(games, key=self.get_game_start_time, reverse=True):
            if self.is_game_final(game):
                last_game = game
                break

        result = "-"
        if last_game:
            result = self.get_game_result_for_team(last_game, team_abbrev)

        self.team_last_game_cache[team_abbrev] = (result, last_game)
        return self.team_last_game_cache[team_abbrev]

    def get_team_schedule(self, team_abbrev):
        """Fetch (and cache) the team's season schedule."""
        if team_abbrev in self.team_schedule_cache:
            return self.team_schedule_cache[team_abbrev]
        season = self.get_current_season()
        try:
            schedule = self.client.schedule.team_season_schedule(team_abbr=team_abbrev, season=season)
            games = schedule.get("games", [])
        except Exception:
            games = []
        self.team_schedule_cache[team_abbrev] = games
        return games

    def get_current_season(self):
        """Return current NHL season string, e.g., 20242025."""
        today = datetime.date.today()
        start_year = today.year if today.month >= 10 else today.year - 1
        return f"{start_year}{start_year + 1}"

    def get_game_start_time(self, game):
        """Return datetime for sorting games chronologically."""
        start_time = game.get("startTimeUTC") or game.get("gameDate")
        if not start_time:
            return datetime.datetime.min
        try:
            return datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        except Exception:
            return datetime.datetime.min

    def is_game_final(self, game):
        """Determine whether a schedule entry represents a completed game."""
        game_state = game.get("gameState", "")
        game_outcome = game.get("gameOutcome", {})
        away_score = game.get("awayTeam", {}).get("score")
        home_score = game.get("homeTeam", {}).get("score")
        has_scores = (
            (away_score is not None and away_score != "" and away_score != 0) or
            (home_score is not None and home_score != "" and home_score != 0)
        )
        has_outcome = bool(game_outcome)
        return game_state in ("FINAL", "OFFICIAL") or has_outcome or (has_scores and game_state == "OFF")

    def get_game_result_for_team(self, game, team_abbrev):
        """Return 'W' or 'L' for the provided team based on the game data."""
        away = game.get("awayTeam", {}).get("abbrev", "")
        home = game.get("homeTeam", {}).get("abbrev", "")
        away_score = game.get("awayTeam", {}).get("score", 0)
        home_score = game.get("homeTeam", {}).get("score", 0)
        try:
            away_score = int(away_score)
        except (ValueError, TypeError):
            away_score = 0
        try:
            home_score = int(home_score)
        except (ValueError, TypeError):
            home_score = 0

        is_home = team_abbrev == home
        is_away = team_abbrev == away
        if not (is_home or is_away):
            return "-"

        team_score = home_score if is_home else away_score
        opp_score = away_score if is_home else home_score
        if team_score > opp_score:
            return "W"
        elif team_score < opp_score:
            return "L"
        return "-"

    def set_comparison_date(self, ranks_dict, stats_dict):
        """Set the date to compare against"""
        self.comparison_date = ranks_dict
        self.comparison_stats = stats_dict
        self.populate_table()
        self.update_sort_indicator()

    def reset_comparison(self):
        """Reset to default 2-day comparison"""
        self.comparison_date = None
        self.comparison_stats = None
        self.populate_table()
        self.update_sort_indicator()

    def get_rainbow_color(self, offset):
        """Generate a rainbow color based on offset (0-360 degrees)"""
        # Cycle through hue from 0 to 360
        hue = (offset % 360) / 360.0
        # Convert HSV to RGB
        # Using a bright, saturated color
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
        """Update rainbow colors for all items in rainbow_items and rainbow_banner_labels"""
        self.rainbow_offset = (self.rainbow_offset + 2) % 360  # Increment by 2 degrees
        for idx, (item, row, col) in enumerate(self.rainbow_items):
            if item and self.table.item(row, col) == item:
                # Add a phase offset based on item index for flowing effect
                phase_offset = (idx * 30) % 360  # Each item offset by 30 degrees
                color = self.get_rainbow_color(self.rainbow_offset + phase_offset)
                item.setForeground(color)
        
        # Update rainbow colors for banner labels (scrolling rainbow effect)
        for idx, label in enumerate(self.rainbow_banner_labels):
            if label and label.isVisible():
                # Add a phase offset based on label index for flowing effect
                # Use a larger offset for banner to create scrolling rainbow effect
                phase_offset = (idx * 20) % 360  # Each label offset by 20 degrees
                color = self.get_rainbow_color(self.rainbow_offset + phase_offset)
                # Update the style sheet with the new color
                style = f"color: rgb({color.red()}, {color.green()}, {color.blue()}); font-size: 12px; font-weight: bold;"
                label.setStyleSheet(style)
    
    def calculate_playoff_status(self, team):
        """Calculate if team would make playoffs if season ended today"""
        div_rank = team.get("divisionSequence", 999)
        wildcard_rank = team.get("wildcardSequence", 999)
        conf_rank = team.get("conferenceSequence", 999)
        points = team.get("points", 0)
        team_abbrev = team.get("teamAbbrev", {}).get("default", "")
        
        # Top 3 in division = in playoffs
        # Top 2 wild cards = in playoffs
        in_playoffs = (div_rank <= 3) or (wildcard_rank <= 2)
        
        # Find all teams that would make playoffs and get the cutoff points
        playoff_teams = []
        for t in self.standings:
            t_div_rank = t.get("divisionSequence", 999)
            t_wildcard_rank = t.get("wildcardSequence", 999)
            if (t_div_rank <= 3) or (t_wildcard_rank <= 2):
                playoff_teams.append(t)
        
        # Sort playoff teams by points (descending) to find the cutoff
        playoff_teams_sorted = sorted(playoff_teams, key=lambda t: t.get("points", 0), reverse=True)
        if len(playoff_teams_sorted) >= 8:
            cutoff_team = playoff_teams_sorted[7]  # 8th team (0-indexed)
            cutoff_points = cutoff_team.get("points", 0)
            points_diff = points - cutoff_points
        else:
            cutoff_points = points if in_playoffs else 0
            points_diff = 0
        
        # Build status message
        if in_playoffs:
            if div_rank <= 3:
                status = f"✔ IN PLAYOFFS\nDivision rank: {div_rank}/8\n"
            else:
                status = f"✔ IN PLAYOFFS\nWild card rank: {wildcard_rank}/8\n"
            status += f"Conference rank: {conf_rank}/16\nPoints: {points}"
            if len(playoff_teams_sorted) >= 8 and points_diff > 0:
                status += f"\n+{points_diff} points ahead of cutoff"
        else:
            status = f"✖ OUT OF PLAYOFFS\nDivision rank: {div_rank}/8\nWild card rank: {wildcard_rank}/8\n"
            status += f"Conference rank: {conf_rank}/16\nPoints: {points}"
            if len(playoff_teams_sorted) >= 8 and cutoff_points > 0:
                status += f"\n{abs(points_diff)} points behind cutoff"
        
        return in_playoffs, status
    
    def get_stat_color(self, abbrev, stat_key, current_value, higher_is_better=True):
        """Get green/red color based on stat comparison with comparison date (default 2 days ago)"""
        # Use custom comparison stats or default to 2 days ago
        if self.comparison_stats:
            compare_stats = self.comparison_stats
        else:
            compare_stats = self.two_days_ago_stats
        
        if not compare_stats or abbrev not in compare_stats:
            return None, None
        
        compare_value = compare_stats[abbrev].get(stat_key, 0)
        
        # Handle float comparison for pointPctg
        if isinstance(current_value, float) or isinstance(compare_value, float):
            current_value = float(current_value)
            compare_value = float(compare_value)
        
        if higher_is_better:
            if current_value > compare_value:
                return QColor("green"), compare_value
            elif current_value < compare_value:
                return QColor("red"), compare_value
        else:
            if current_value < compare_value:
                return QColor("green"), compare_value
            elif current_value > compare_value:
                return QColor("red"), compare_value
        
        return None, None

    def open_playoff_window(self):
        self.playoff_window = PlayoffWindow()
        self.playoff_window.show()

    def populate_table(self, refresh_banner=True):
        # Clear previous rainbow items
        self.rainbow_items = []
        
        self.table.setRowCount(len(self.standings))
        favorite_rows = set()
        
        for row, team in enumerate(self.standings):
            abbrev = team.get("teamAbbrev", {}).get("default", "")
            full_name = team.get('teamName', {}).get('default', '')
            current_rank = team.get("leagueSequence", "")
            
            # Use custom comparison date or 2 days ago
            if self.comparison_date:
                compare_ranks = self.comparison_date
            else:
                compare_ranks = self.two_days_ago_ranks
            
            prev_rank = compare_ranks.get(abbrev, current_rank)
            delta = prev_rank - current_rank if isinstance(current_rank, int) and isinstance(prev_rank, int) else 0
            
            arrow = ""
            color = None
            if delta > 0:
                arrow = " ↑"
                color = QColor("green")
            elif delta < 0:
                arrow = " ↓"
                color = QColor("red")
            
            # Add star if favorited
            star = "★ " if abbrev in self.favorite_teams else ""
            rank_item = QTableWidgetItem(f"{star}{current_rank}{arrow}")
            if color:
                if color.name() == "#008000" and abbrev in self.favorite_teams:  # Green and favorite
                    # Add to rainbow items instead of setting green
                    self.rainbow_items.append((rank_item, row, 0))
                else:
                    rank_item.setForeground(color)
                # Add tooltip showing the rank change
                if isinstance(current_rank, int) and isinstance(prev_rank, int) and prev_rank != current_rank:
                    rank_item.setToolTip(f"{prev_rank} → {current_rank}")
            self.table.setItem(row, 0, rank_item)
            
            if abbrev in self.favorite_teams:
                favorite_rows.add(row)

            team_item = QTableWidgetItem(abbrev)
            team_item.setToolTip(full_name)
            self.table.setItem(row, 1, team_item)

            self.table.setItem(row, 2, QTableWidgetItem(str(team.get("gamesPlayed", 0))))
            
            # Wins (column 3) - higher is better
            wins_item = QTableWidgetItem(str(team.get("wins", 0)))
            wins_color, wins_compare = self.get_stat_color(abbrev, "wins", team.get("wins", 0), higher_is_better=True)
            if wins_color and wins_compare is not None:
                wins_item.setForeground(wins_color)
                wins_item.setToolTip(f"{wins_compare} → {team.get('wins', 0)}")
            self.table.setItem(row, 3, wins_item)
            
            self.table.setItem(row, 4, QTableWidgetItem(str(team.get("losses", 0))))
            self.table.setItem(row, 5, QTableWidgetItem(str(team.get("otLosses", 0))))
            
            # Points (column 6) - higher is better
            points_item = QTableWidgetItem(str(team.get("points", 0)))
            points_color, points_compare = self.get_stat_color(abbrev, "points", team.get("points", 0), higher_is_better=True)
            if points_color and points_compare is not None:
                points_item.setForeground(points_color)
                points_item.setToolTip(f"{points_compare} → {team.get('points', 0)}")
            self.table.setItem(row, 6, points_item)
            
            self.table.setItem(row, 7, QTableWidgetItem(str(team.get("regulationPlusOtWins", 0))))
            
            # Point Percentage (column 8) - higher is better
            pctg_value = team.get('pointPctg', 0.0)
            pctg_item = QTableWidgetItem(f"{pctg_value:.3f}")
            pctg_color, pctg_compare = self.get_stat_color(abbrev, "pointPctg", pctg_value, higher_is_better=True)
            if pctg_color and pctg_compare is not None:
                pctg_item.setForeground(pctg_color)
                pctg_item.setToolTip(f"{pctg_compare:.3f} → {pctg_value:.3f}")
            self.table.setItem(row, 8, pctg_item)
            
            # Goals For (column 9) - higher is better
            gf_item = QTableWidgetItem(str(team.get("goalFor", 0)))
            gf_color, gf_compare = self.get_stat_color(abbrev, "goalFor", team.get("goalFor", 0), higher_is_better=True)
            if gf_color and gf_compare is not None:
                gf_item.setForeground(gf_color)
                gf_item.setToolTip(f"{gf_compare} → {team.get('goalFor', 0)}")
            self.table.setItem(row, 9, gf_item)
            
            # Goals Against (column 10) - lower is better
            ga_item = QTableWidgetItem(str(team.get("goalAgainst", 0)))
            ga_color, ga_compare = self.get_stat_color(abbrev, "goalAgainst", team.get("goalAgainst", 0), higher_is_better=False)
            if ga_color and ga_compare is not None:
                ga_item.setForeground(ga_color)
                ga_item.setToolTip(f"{ga_compare} → {team.get('goalAgainst', 0)}")
            self.table.setItem(row, 10, ga_item)
            
            # Goal Differential (column 11) - higher is better
            diff_item = QTableWidgetItem(str(team.get("goalDifferential", 0)))
            diff_color, diff_compare = self.get_stat_color(abbrev, "goalDifferential", team.get("goalDifferential", 0), higher_is_better=True)
            if diff_color and diff_compare is not None:
                diff_item.setForeground(diff_color)
                diff_item.setToolTip(f"{diff_compare} → {team.get('goalDifferential', 0)}")
            self.table.setItem(row, 11, diff_item)
            home_record = f"{team.get('homeWins',0)}-{team.get('homeLosses',0)}-{team.get('homeOtLosses',0)}"
            self.table.setItem(row, 12, QTableWidgetItem(home_record))
            road_record = f"{team.get('roadWins',0)}-{team.get('roadLosses',0)}-{team.get('roadOtLosses',0)}"
            self.table.setItem(row, 13, QTableWidgetItem(road_record))
            l10_record = f"{team.get('l10Wins',0)}-{team.get('l10Losses',0)}-{team.get('l10OtLosses',0)}"
            self.table.setItem(row, 14, QTableWidgetItem(l10_record))
            streak_code = team.get("streakCode", "")
            streak_count = team.get("streakCount", 0)
            streak = f"{streak_code}{streak_count}" if streak_count else ""
            self.table.setItem(row, 15, QTableWidgetItem(streak))

            # Last game result column
            if self.last_game_col != -1:
                last_result = self.get_last_result_letter(team)
                display_result = last_result if last_result in ("W", "L") else "—"
                last_item = QTableWidgetItem(display_result)
                last_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if display_result == "W":
                    if abbrev in self.favorite_teams:
                        self.rainbow_items.append((last_item, row, self.last_game_col))
                    else:
                        last_item.setForeground(QColor("green"))
                elif display_result == "L":
                    last_item.setForeground(QColor("red"))
                last_item.setToolTip("Click to open the most recent completed game")
                self.table.setItem(row, self.last_game_col, last_item)
            
            # Playoff status column
            in_playoffs, playoff_tooltip = self.calculate_playoff_status(team)
            playoff_symbol = "✔" if in_playoffs else "✖"
            playoff_item = QTableWidgetItem(playoff_symbol)
            playoff_item.setToolTip(playoff_tooltip)
            
            # Make rainbow colored if it has a check (could go to playoffs) AND it's a favorite team
            if in_playoffs and abbrev in self.favorite_teams and self.playoff_col != -1:
                self.rainbow_items.append((playoff_item, row, self.playoff_col))
            
            if self.playoff_col != -1:
                self.table.setItem(row, self.playoff_col, playoff_item)

            if self.advanced_mode:
                advanced_start = self.basic_column_count
                advanced_values = [
                    str(team.get("regulationWins", 0)),
                    str(team.get("shootoutWins", 0)),
                    str(team.get("shootoutLosses", 0)),
                    str(team.get("conferenceSequence", 0)),
                    str(team.get("divisionSequence", 0)),
                    str(team.get("wildcardSequence", 0)),
                ]
                for offset, value in enumerate(advanced_values):
                    self.table.setItem(row, advanced_start + offset, QTableWidgetItem(value))

        # Apply favorite highlight delegate
        delegate = FavoriteDelegate(favorite_rows, self.table)
        self.table.setItemDelegate(delegate)

        if refresh_banner:
            self.refresh_banner()

    def get_sort_key(self, col):
        basic_keys = [
            lambda t: int(t.get("leagueSequence", 999)),
            lambda t: t.get("teamAbbrev", {}).get("default", "").lower(),
            lambda t: int(t.get("gamesPlayed", 0)),
            lambda t: int(t.get("wins", 0)),
            lambda t: int(t.get("losses", 0)),
            lambda t: int(t.get("otLosses", 0)),
            lambda t: int(t.get("points", 0)),
            lambda t: int(t.get("regulationPlusOtWins", 0)),
            lambda t: float(t.get("pointPctg", 0)),
            lambda t: int(t.get("goalFor", 0)),
            lambda t: int(t.get("goalAgainst", 0)),
            lambda t: int(t.get("goalDifferential", 0)),
            lambda t: (t.get("homeWins",0), -t.get("homeLosses",0), -t.get("homeOtLosses",0)),
            lambda t: (t.get("roadWins",0), -t.get("roadLosses",0), -t.get("roadOtLosses",0)),
            lambda t: (t.get("l10Wins",0), -t.get("l10Losses",0), -t.get("l10OtLosses",0)),
            lambda t: (1 if t.get("streakCode", "") == "W" else (-1 if t.get("streakCode", "") == "L" else 0)) * t.get("streakCount", 0),
            lambda t, self=self: 1 if self.get_last_result_letter(t) == "W" else (-1 if self.get_last_result_letter(t) == "L" else 0),
            lambda t: (t.get("divisionSequence", 999) <= 3) or (t.get("wildcardSequence", 999) <= 2),  # Playoffs (True = in, False = out)
        ]
        advanced_keys = [
            lambda t: int(t.get("regulationWins", 0)),
            lambda t: int(t.get("shootoutWins", 0)),
            lambda t: int(t.get("shootoutLosses", 0)),
            lambda t: int(t.get("conferenceSequence", 999)),
            lambda t: int(t.get("divisionSequence", 999)),
            lambda t: int(t.get("wildcardSequence", 999)),
        ]
        keys = basic_keys + advanced_keys if self.advanced_mode else basic_keys
        return keys[col]

    def handle_header_click(self, col):
        if self.current_sort_col == col:
            self.current_sort_order = (self.current_sort_order + 1) % 3
        else:
            self.current_sort_col = col
            self.current_sort_order = 1  # start ascending

        # Actually sort the data
        if self.current_sort_order == 0:
            self.standings = list(self.original_standings)
        else:
            key = self.get_sort_key(col)
            reverse = (self.current_sort_order == 2)
            self.standings = sorted(self.original_standings, key=key, reverse=reverse)

        self.populate_table(refresh_banner=False)
        self.update_sort_indicator()

    def update_sort_indicator(self):
        header = self.table.horizontalHeader()
        if self.current_sort_order == 0:
            header.setSortIndicatorShown(False)
        else:
            order = Qt.SortOrder.AscendingOrder if self.current_sort_order == 1 else Qt.SortOrder.DescendingOrder
            header.setSortIndicator(self.current_sort_col, order)
            header.setSortIndicatorShown(True)

