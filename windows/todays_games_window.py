import datetime
import json
import os
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QScrollArea, QLabel, 
    QFrame, QHBoxLayout, QPushButton, QGridLayout, QProgressDialog, QApplication,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QSize, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QPixmap, QFont, QCursor, QPainter, QPainterPath
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from nhlpy import NHLClient
from .game_details_window import GameDetailsWindow

class GameCard(QFrame):
    clicked = pyqtSignal(dict)  # Signal emitting the game data when clicked

    def __init__(self, game, favorite_teams, parent=None):
        super().__init__(parent)
        self.game = game
        self.favorite_teams = favorite_teams
        self.network_manager = QNetworkAccessManager()
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setObjectName("GameCard")
        
        # Determine if this is a favorite game
        self.away_abbrev = game.get("awayTeam", {}).get("abbrev", "N/A")
        self.home_abbrev = game.get("homeTeam", {}).get("abbrev", "N/A")
        self.is_favorite = (self.away_abbrev in favorite_teams or self.home_abbrev in favorite_teams)

        # Main Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)

        # --- Header (Status | Venue | TV) ---
        header_layout = QHBoxLayout()
        
        self.status_label = QLabel(self.get_status_text())
        self.status_label.setStyleSheet("font-weight: bold; color: #e0e0e0;")
        
        venue_text = game.get("venue", {}).get("default", "")
        self.venue_label = QLabel(venue_text)
        self.venue_label.setStyleSheet("color: #aaaaaa; font-size: 10px;")
        
        tv_broadcasts = game.get("tvBroadcasts", [])
        tv_text = ", ".join(b.get("network", "") for b in tv_broadcasts) if tv_broadcasts else ""
        self.tv_label = QLabel(f"{tv_text}" if tv_text else "")
        self.tv_label.setStyleSheet("color: #888888; font-size: 10px;")
        self.tv_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        header_layout.addWidget(self.status_label)
        header_layout.addStretch()
        header_layout.addWidget(self.venue_label)
        header_layout.addStretch()
        header_layout.addWidget(self.tv_label)
        self.layout.addLayout(header_layout)

        # --- Divider ---
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #444; margin-bottom: 5px;")
        self.layout.addWidget(line)

        # --- Teams and Scores Area ---
        teams_layout = QHBoxLayout()

        # Away Team
        self.away_logo = QLabel()
        self.away_logo.setFixedSize(60, 60)
        self.away_logo.setScaledContents(True)
        self.load_logo(self.away_abbrev, self.away_logo)
        
        away_layout = QVBoxLayout()
        away_layout.addWidget(self.away_logo, alignment=Qt.AlignmentFlag.AlignCenter)
        away_name = QLabel(self.away_abbrev)
        away_name.setStyleSheet("font-weight: bold; font-size: 14px;")
        away_layout.addWidget(away_name, alignment=Qt.AlignmentFlag.AlignCenter)

        # Scores / VS
        score_layout = QHBoxLayout()
        self.away_score_label = QLabel(str(game.get("awayTeam", {}).get("score", 0)))
        self.home_score_label = QLabel(str(game.get("homeTeam", {}).get("score", 0)))
        
        score_style = "font-size: 24px; font-weight: bold; color: white;"
        self.away_score_label.setStyleSheet(score_style)
        self.home_score_label.setStyleSheet(score_style)

        # VS Label or Dash
        vs_label = QLabel("vs" if self.get_game_state() == "PRE" else "-")
        vs_label.setStyleSheet("color: #888; font-size: 14px; margin: 0 10px;")

        score_layout.addWidget(self.away_score_label)
        score_layout.addWidget(vs_label)
        score_layout.addWidget(self.home_score_label)

        # Home Team
        self.home_logo = QLabel()
        self.home_logo.setFixedSize(60, 60)
        self.home_logo.setScaledContents(True)
        self.load_logo(self.home_abbrev, self.home_logo)

        home_layout = QVBoxLayout()
        home_layout.addWidget(self.home_logo, alignment=Qt.AlignmentFlag.AlignCenter)
        home_name = QLabel(self.home_abbrev)
        home_name.setStyleSheet("font-weight: bold; font-size: 14px;")
        home_layout.addWidget(home_name, alignment=Qt.AlignmentFlag.AlignCenter)

        teams_layout.addLayout(away_layout)
        teams_layout.addStretch()
        teams_layout.addLayout(score_layout)
        teams_layout.addStretch()
        teams_layout.addLayout(home_layout)

        self.layout.addLayout(teams_layout)

        # Style the card
        self.update_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.game)
        super().mousePressEvent(event)

    def load_logo(self, abbrev, label_widget):
        # Map NHL API abbreviations (Keys) to ESPN URL codes (Values)
        espn_mapping = {
            "LAK": "la",    # Los Angeles Kings
            "TBL": "tb",    # Tampa Bay Lightning
            "NJD": "nj",    # New Jersey Devils
            "SJS": "sj",    # San Jose Sharks
            "UTA": "utah",  # Utah Hockey Club
            "VEG": "vgk"    # Vegas sometimes varies
        }

        if abbrev in espn_mapping:
            abbrev = espn_mapping[abbrev]
        
        url = f"https://assets.espn.go.com/i/teamlogos/nhl/500/{abbrev}.png"
        request = QNetworkRequest(QUrl(url))
        reply = self.network_manager.get(request)
        reply.finished.connect(lambda: self.on_logo_loaded(reply, label_widget))

    def on_logo_loaded(self, reply, label_widget):
        request_url = reply.request().url().toString()
        
        if reply.error() == reply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            if not pixmap.isNull():
                label_widget.setPixmap(pixmap)
            else:
                label_widget.setText(f"BAD IMG\n{request_url}")
                label_widget.setToolTip(f"Data downloaded but not a valid image.\nURL: {request_url}")
                label_widget.setStyleSheet("QLabel { color: #ff5555; font-size: 8px; border: 1px solid #ff5555; padding: 2px; }")
                label_widget.setWordWrap(True)
                label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            label_widget.setText(f"LINK ERR\n{request_url}")
            label_widget.setToolTip(f"Failed to fetch image.\nError: {reply.errorString()}\nURL: {request_url}")
            label_widget.setStyleSheet("QLabel { color: #ff5555; font-size: 8px; border: 1px solid #ff5555; padding: 2px; }")
            label_widget.setWordWrap(True)
            label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
        reply.deleteLater()

    def get_game_state(self):
        state = self.game.get("gameState", "")
        if state in ["FINAL", "OFFICIAL"]: return "FINAL"
        if state == "LIVE": return "LIVE"
        return "PRE"

    def get_status_text(self):
        state = self.game.get("gameState", "")
        if state == "LIVE":
            period = self.game.get("period", 1)
            clock = self.game.get("clock", {}).get("timeRemaining", "IN PROG")
            return f"LIVE - P{period} {clock}"
        elif state in ["FINAL", "OFFICIAL"]:
            return "FINAL"
        else:
            start_time = self.game.get("startTimeUTC", "")
            if start_time:
                try:
                    utc_time = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    est_time = utc_time - datetime.timedelta(hours=5)
                    return est_time.strftime("%I:%M %p EST")
                except:
                    return "UPCOMING"
            return "UPCOMING"

    def update_style(self):
        base_style = """
            QFrame#GameCard {
                background-color: #2b2b2b;
                border-radius: 10px;
                border: 1px solid #444;
            }
            QFrame#GameCard:hover {
                background-color: #353535;
                border: 1px solid #666;
            }
        """
        
        if self.is_favorite:
            base_style += """
                QFrame#GameCard {
                    border: 2px solid #FFD700;
                }
            """
            
            if self.get_game_state() == "FINAL":
                away_score = int(self.game.get("awayTeam", {}).get("score", 0))
                home_score = int(self.game.get("homeTeam", {}).get("score", 0))
                
                away_fav = self.away_abbrev in self.favorite_teams
                home_fav = self.home_abbrev in self.favorite_teams
                
                fav_won = (away_fav and away_score > home_score) or (home_fav and home_score > away_score)
                
                if fav_won:
                    base_style += """
                        QFrame#GameCard {
                            border: 3px solid;
                            border-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                stop:0 red, stop:0.2 orange, stop:0.4 yellow, 
                                stop:0.6 green, stop:0.8 blue, stop:1 violet);
                        }
                    """

        self.setStyleSheet(base_style)


class TodaysGamesWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NHL Schedule")
        self.resize(550, 700)

        self.client = NHLClient()
        self.games = []
        self.favorites_file = os.path.join(os.path.expanduser("~"), ".nhl_favorites.json")
        self.favorite_teams = set()
        
        # Track the current date being viewed
        self.current_date = datetime.date.today()
        
        self.load_favorites()
        self.init_ui()
        
        # Load games after UI is ready
        QTimer.singleShot(100, self.fetch_games_with_loading)

    def load_favorites(self):
        try:
            if os.path.exists(self.favorites_file):
                with open(self.favorites_file, 'r') as f:
                    self.favorite_teams = set(json.load(f))
        except Exception:
            self.favorite_teams = set()

    def init_ui(self):
        central = QWidget()
        central.setStyleSheet("background-color: #1e1e1e; color: white;")
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)

        # --- Date Navigation Header ---
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 5, 0, 5)

        # Previous Button
        self.prev_btn = QPushButton("<")
        self.prev_btn.setFixedSize(40, 30)
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 5px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #444; }
        """)
        self.prev_btn.clicked.connect(self.go_prev_day)

        # Date Label
        self.date_label = QLabel()
        self.date_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_date_header()

        # Next Button
        self.next_btn = QPushButton(">")
        self.next_btn.setFixedSize(40, 30)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 5px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #444; }
        """)
        self.next_btn.clicked.connect(self.go_next_day)

        header_layout.addWidget(self.prev_btn)
        header_layout.addStretch()
        header_layout.addWidget(self.date_label)
        header_layout.addStretch()
        header_layout.addWidget(self.next_btn)

        main_layout.addLayout(header_layout)

        # --- Scroll Area for Games ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("""
            QScrollArea { background-color: transparent; }
            QWidget { background-color: transparent; }
            QScrollBar:vertical {
                border: none;
                background: #2b2b2b;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #555;
                min-height: 20px;
                border-radius: 5px;
            }
        """)

        self.games_container = QWidget()
        self.games_layout = QVBoxLayout(self.games_container)
        self.games_layout.setSpacing(15)
        self.games_layout.addStretch() # Push items up

        self.scroll_area.setWidget(self.games_container)
        main_layout.addWidget(self.scroll_area)

        # Refresh Button
        refresh_btn = QPushButton("Refresh Scores")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
                border: 1px solid #555;
            }
            QPushButton:hover { background-color: #555; }
            QPushButton:pressed { background-color: #333; }
        """)
        refresh_btn.clicked.connect(self.fetch_games_with_loading)
        main_layout.addWidget(refresh_btn)

    def go_prev_day(self):
        self.current_date -= datetime.timedelta(days=1)
        self.update_date_header()
        self.fetch_games_with_loading()

    def go_next_day(self):
        self.current_date += datetime.timedelta(days=1)
        self.update_date_header()
        self.fetch_games_with_loading()

    def update_date_header(self):
        # Format: "October 12, 2023"
        self.date_label.setText(self.current_date.strftime('%B %d, %Y'))

    def fetch_games_with_loading(self):
        # Show loading only if we don't have games yet or switching days
        dialog = QProgressDialog(f"Loading games for {self.current_date}...", None, 0, 0, self)
        dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
        dialog.setMinimumDuration(0)
        dialog.setStyleSheet("QProgressDialog { background-color: #333; color: white; }")
        dialog.show()
        QApplication.processEvents()
        
        target_date = self.current_date.isoformat()
        try:
            sched = self.client.schedule.daily_schedule(date=target_date)
            self.games = sched.get("games", [])
            self.populate_games_list()
        except Exception as e:
            print(f"Error loading games: {e}")
            self.games = []
        
        dialog.close()

    def populate_games_list(self):
        # Clear existing items
        while self.games_layout.count():
            child = self.games_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.spacerItem():
                self.games_layout.removeItem(child)

        if not self.games:
            no_games_label = QLabel("No games scheduled.")
            no_games_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_games_label.setStyleSheet("color: #888; font-size: 16px; margin-top: 50px;")
            self.games_layout.addWidget(no_games_label)
        else:
            for game in self.games:
                card = GameCard(game, self.favorite_teams)
                card.clicked.connect(self.open_game_details)
                self.games_layout.addWidget(card)
        
        self.games_layout.addStretch()

    def open_game_details(self, game):
        self.game_details_window = GameDetailsWindow(game, self.client)
        self.game_details_window.show()
