import datetime
import re
import webbrowser
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QLabel, QScrollArea, QGridLayout,
    QFrame, QHBoxLayout, QPushButton
)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QFont, QColor, QPalette
from PyQt6.QtWebEngineWidgets import QWebEngineView


class GameDetailsWindow(QMainWindow):
    def __init__(self, game, client):
        super().__init__()
        self.game = game
        self.client = client
        self.game_id = game.get("id", "")
        
        # Set window title with improved team detection
        away_team = game.get("awayTeam", {})
        home_team = game.get("homeTeam", {})
        venue = game.get("venue", {})
        venue_name = venue.get("default", "")
        
        # Try to get team names with fallbacks
        away = (away_team.get("abbrev", "") or 
               away_team.get("name", {}).get("default", "") or 
               away_team.get("placeName", {}).get("default", "") or 
               "Away")
        home = (home_team.get("abbrev", "") or 
               home_team.get("name", {}).get("default", "") or 
               home_team.get("placeName", {}).get("default", "") or 
               "Home")
        
        # If still missing, try teams array
        if away == "Away" or home == "Home":
            teams = game.get("teams", [])
            if teams:
                for team in teams:
                    team_name = team.get("abbrev", "") or team.get("name", {}).get("default", "")
                    team_venue = team.get("placeName", {}).get("default", "")
                    if team_venue and venue_name and team_venue.lower() in venue_name.lower():
                        home = team_name or home
                    elif away == "Away":
                        away = team_name or away
        
        self.setWindowTitle(f"{away} @ {home} - Game Details")
        self.resize(900, 700)
        
        # Timer for live updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_game_data)
        self.is_live = False
        
        self.init_ui()
        self.update_game_data()
        
        # Start timer if game is live
        game_state = game.get("gameState", "")
        if game_state == "LIVE":
            self.is_live = True
            self.update_timer.start(5000)  # Update every 5 seconds
    
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header frame with score (no rounded corners)
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.Shape.StyledPanel)
        header_frame.setStyleSheet("background-color: #1a1a1a;") # Removed padding to control it with margins/layouts
        header_layout = QVBoxLayout(header_frame)
        header_layout.setSpacing(10)
        
        # --- Stream Now Banner Button at the top of the header ---
        self.stream_now_button = QPushButton("STREAM NOW")
        self.stream_now_button.setStyleSheet("""
            QPushButton {
                background-color: #E31837; /* NHL Red */
                color: white;
                border: none;
                padding: 8px; /* Larger padding for banner look */
                font-weight: bold;
                font-size: 14px;
                margin: 0px -20px 10px -20px; /* Set top margin to 0 to prevent clipping, keep side margins for full width */
            }
            QPushButton:hover {
                background-color: #c41530;
            }
        """)
        self.stream_now_button.clicked.connect(self.open_stream_now)
        header_layout.addWidget(self.stream_now_button)
        # ---------------------------------------------------------
        
        # Score display at top (large and prominent)
        
        # Score display at top (large and prominent)
        
        # Add padding to the score/status section
        score_status_widget = QWidget()
        score_status_layout = QVBoxLayout(score_status_widget)
        score_status_layout.setContentsMargins(20, 10, 20, 10) # Add padding back for score/status
        
        self.score_label = QLabel()
        score_font = QFont()
        score_font.setPointSize(42)
        score_font.setBold(True)
        self.score_label.setFont(score_font)
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_label.setStyleSheet("color: white;")
        header_layout.addWidget(self.score_label)
        
        # Status label below score
        self.status_label = QLabel()
        status_font = QFont()
        status_font.setPointSize(16)
        status_font.setBold(True)
        self.status_label.setFont(status_font)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #cccccc;")
        score_status_layout.addWidget(self.status_label)
        
        header_layout.addWidget(score_status_widget) # Add the padded widget to the header layout
        
        # Buttons for external links
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        

        
        self.moneypuck_button = QPushButton("View on MoneyPuck.com")
        self.moneypuck_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.moneypuck_button.clicked.connect(self.open_moneypuck)
        button_layout.addWidget(self.moneypuck_button)
        
        self.nhl_button = QPushButton("View on NHL.com")
        self.nhl_button.setStyleSheet("""
            QPushButton {
                background-color: #003E7E;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0052a3;
            }
            QPushButton:pressed {
                background-color: #002d5a;
            }
        """)
        self.nhl_button.clicked.connect(self.open_nhl)
        button_layout.addWidget(self.nhl_button)
        
        self.tsn_button = QPushButton("View on TSN.ca")
        self.tsn_button.setStyleSheet("""
            QPushButton {
                background-color: #c62828;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
            QPushButton:pressed {
                background-color: #8e0000;
            }
        """)
        self.tsn_button.clicked.connect(self.open_tsn)
        button_layout.addWidget(self.tsn_button)
        
        button_layout.addStretch()
        header_layout.addLayout(button_layout)
        
        layout.addWidget(header_frame)
        
        # Scroll area for game details
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: #f5f5f5; border: none;")
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        
        # Game details grid
        self.details_grid = QGridLayout()
        self.details_grid.setSpacing(12)
        self.details_grid.setColumnStretch(0, 1)
        self.details_grid.setColumnStretch(1, 2)
        scroll_layout.addLayout(self.details_grid)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Store labels for updates
        self.detail_labels = {}
    
    def update_game_data(self):
        """Fetch and update game data"""
        try:
            # Try to get fresh game data
            # First, try to get from schedule (might have updated data)
            today = datetime.date.today()
            day_str = today.isoformat()
            try:
                sched = self.client.schedule.daily_schedule(date=day_str)
                games = sched.get("games", [])
                # Find our game
                for g in games:
                    if g.get("id") == self.game_id:
                        self.game = g
                        break
            except Exception:
                pass  # Use existing game data if fetch fails
            
            # Get teams - use venue to determine home/away if needed
            away_team = self.game.get("awayTeam", {})
            home_team = self.game.get("homeTeam", {})
            venue = self.game.get("venue", {})
            venue_name = venue.get("default", "")
            
            # If teams are missing, try to determine from venue or other fields
            if not away_team or not home_team:
                # Try teams array
                teams = self.game.get("teams", [])
                if teams and len(teams) >= 2:
                    # Check which team's venue matches
                    for team in teams:
                        team_venue = team.get("placeName", {}).get("default", "")
                        if team_venue and venue_name and team_venue.lower() in venue_name.lower():
                            if not home_team:
                                home_team = team
                        elif not away_team:
                            away_team = team
                
                # Fallback: if still missing, use first two teams
                if teams and len(teams) >= 2:
                    if not away_team:
                        away_team = teams[0]
                    if not home_team:
                        home_team = teams[1] if len(teams) > 1 else teams[0]
            
            # Get team names with fallbacks
            away_name = (away_team.get("abbrev", "") or 
                        away_team.get("name", {}).get("default", "") or 
                        away_team.get("placeName", {}).get("default", "") or 
                        "Away")
            home_name = (home_team.get("abbrev", "") or 
                        home_team.get("name", {}).get("default", "") or 
                        home_team.get("placeName", {}).get("default", "") or 
                        "Home")
            
            away_score = away_team.get("score", 0) if away_team.get("score") is not None else 0
            home_score = home_team.get("score", 0) if home_team.get("score") is not None else 0
            
            game_state = self.game.get("gameState", "")
            game_outcome = self.game.get("gameOutcome", {}) or {}

            # Determine if this game should be treated as completed even if the
            # raw gameState isn't "FINAL" or "OFFICIAL". The API can sometimes
            # leave gameState as "OFF" or another value for past games, but the
            # presence of a gameOutcome or non‑zero scores tells us it's done.
            has_scores = (
                (away_score is not None and away_score != "" and away_score != 0)
                or (home_score is not None and home_score != "" and home_score != 0)
            )
            has_outcome = bool(game_outcome)
            is_final_like = game_state in ["FINAL", "OFFICIAL"] or has_outcome or has_scores
            
            # Format score
            if game_state == "LIVE" or (away_score is not None and away_score != "" and home_score is not None and home_score != ""):
                score_text = f"{away_name} {away_score} - {home_score} {home_name}"
            else:
                score_text = f"{away_name} - - {home_name}"
            
            self.score_label.setText(score_text)
            
            # Update status
            period_descriptor = self.game.get("periodDescriptor", {}) or {}

            # Try to determine the correct period; the raw "period" field can be 0
            # for live games depending on the API response shape.
            period = self.game.get("period")
            if not period:
                for key in ("number", "periodNumber", "period"):
                    value = period_descriptor.get(key)
                    if isinstance(value, int) and value > 0:
                        period = value
                        break

            if not period and game_state == "LIVE":
                # Avoid showing "Period 0" while the game is clearly in progress
                period = 1

            period_type = period_descriptor.get("periodType", "")
            
            if game_state == "LIVE":
                if period_type == "OT":
                    status = f"Overtime - Period {period}"
                elif period_type == "SO":
                    status = "Shootout"
                else:
                    status = f"Period {period}" if period else "In Progress"
                # Try to get time remaining
                clock = self.game.get("clock", {})
                time_remaining = clock.get("timeRemaining", "")
                if time_remaining:
                    status += f" - {time_remaining}"
            elif is_final_like:
                # Game is finished - show a final status. Use gameOutcome if present
                # to distinguish OT / SO endings.
                last_period_type = game_outcome.get("lastPeriodType", "")
                if last_period_type == "OT":
                    status = "Final (OT)"
                elif last_period_type == "SO":
                    status = "Final (SO)"
                else:
                    status = "Final"
            else:
                # Game hasn't started
                start_time = self.game.get("startTimeUTC", "")
                if start_time:
                    utc_time = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    est_time = utc_time - datetime.timedelta(hours=5)
                    status = f"Scheduled: {est_time.strftime('%I:%M %p EST')}"
                else:
                    status = "Scheduled"
            
            self.status_label.setText(status)
            
            # Update game details
            self.update_details()
            
            # Stop timer if game is finished
            if game_state in ["FINAL", "OFFICIAL"]:
                self.is_live = False
                self.update_timer.stop()
                
        except Exception as e:
            print(f"Error updating game data: {e}")
    
    def update_details(self):
        """Update the game details grid"""
        # Clear existing labels
        for i in reversed(range(self.details_grid.count())):
            item = self.details_grid.itemAt(i)
            if item:
                widget = item.widget()
                if widget:
                    widget.setParent(None)
        
        row = 0
        
        # Get teams with fallback logic
        away_team = self.game.get("awayTeam", {})
        home_team = self.game.get("homeTeam", {})
        venue = self.game.get("venue", {})
        venue_name = venue.get("default", "")
        
        # If teams are missing, try to infer from venue or other data
        if not away_team or not home_team:
            # Try to get from other fields
            teams = self.game.get("teams", [])
            if teams and len(teams) >= 2:
                # Usually first is away, second is home
                if not away_team:
                    away_team = teams[0] if teams[0].get("placeName", {}).get("default", "") != venue_name else teams[1]
                if not home_team:
                    home_team = teams[1] if teams[1].get("placeName", {}).get("default", "") == venue_name else teams[0]
        
        # Team Information Section
        self.add_section_header("Team Information", row)
        row += 1
        
        # Away team info
        away_name = away_team.get("name", {}).get("default", "") or away_team.get("abbrev", "") or "Away Team"
        self.add_detail("Away Team", away_name, row)
        row += 1
        
        away_record = away_team.get("record", "")
        if away_record:
            self.add_detail("Away Team Record", away_record, row)
            row += 1
        
        # Home team info
        home_name = home_team.get("name", {}).get("default", "") or home_team.get("abbrev", "") or "Home Team"
        self.add_detail("Home Team", home_name, row)
        row += 1
        
        home_record = home_team.get("record", "")
        if home_record:
            self.add_detail("Home Team Record", home_record, row)
            row += 1
        
        # Game Information Section
        self.add_section_header("Game Information", row)
        row += 1
        
        # Venue
        if venue_name:
            self.add_detail("Venue", venue_name, row)
            row += 1
        
        # Start time
        start_time = self.game.get("startTimeUTC", "")
        if start_time:
            utc_time = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            est_time = utc_time - datetime.timedelta(hours=5)
            time_str = est_time.strftime("%B %d, %Y at %I:%M %p EST")
            self.add_detail("Start Time", time_str, row)
            row += 1
        
        # TV broadcasts
        tv_broadcasts = self.game.get("tvBroadcasts", [])
        if tv_broadcasts:
            tv_str = ", ".join(b.get("network", "") for b in tv_broadcasts)
            self.add_detail("TV Broadcasts", tv_str, row)
            row += 1
        
        # Game type
        game_type = self.game.get("gameType", "")
        if game_type:
            type_map = {
                1: "Preseason",
                2: "Regular Season",
                3: "Playoffs"
            }
            self.add_detail("Game Type", type_map.get(game_type, f"Type {game_type}"), row)
            row += 1
        
        # Game ID
        if self.game_id:
            self.add_detail("Game ID", str(self.game_id), row)
            row += 1
        
        # Statistics Section (if game is live or finished)
        game_state = self.game.get("gameState", "")
        if game_state in ["LIVE", "FINAL", "OFFICIAL"]:
            self.add_section_header("Game Statistics", row)
            row += 1
            
            # Shots on goal
            away_shots = away_team.get("sog", "") or away_team.get("shotsOnGoal", "")
            home_shots = home_team.get("sog", "") or home_team.get("shotsOnGoal", "")
            if away_shots or home_shots:
                shots_str = f"{away_shots or 0} - {home_shots or 0}"
                self.add_detail("Shots on Goal", shots_str, row)
                row += 1
            
            # Power play opportunities
            away_pp = away_team.get("powerPlay", {})
            home_pp = home_team.get("powerPlay", {})
            if away_pp or home_pp:
                away_pp_opps = away_pp.get("opportunities", "")
                home_pp_opps = home_pp.get("opportunities", "")
                if away_pp_opps is not None or home_pp_opps is not None:
                    pp_str = f"{away_pp_opps or 0}/{away_pp.get('conversions', '') or 0} - {home_pp_opps or 0}/{home_pp.get('conversions', '') or 0}"
                    self.add_detail("Power Play", pp_str, row)
                    row += 1
            
            # Faceoff wins
            away_faceoffs = away_team.get("faceoffWinningPctg", "")
            home_faceoffs = home_team.get("faceoffWinningPctg", "")
            if away_faceoffs is not None or home_faceoffs is not None:
                faceoff_str = f"{away_faceoffs or 0:.1f}% - {home_faceoffs or 0:.1f}%"
                self.add_detail("Faceoff Win %", faceoff_str, row)
                row += 1
            
            # Hits
            away_hits = away_team.get("hits", "")
            home_hits = home_team.get("hits", "")
            if away_hits is not None or home_hits is not None:
                hits_str = f"{away_hits or 0} - {home_hits or 0}"
                self.add_detail("Hits", hits_str, row)
                row += 1
            
            # Blocked shots
            away_blocks = away_team.get("blocks", "")
            home_blocks = home_team.get("blocks", "")
            if away_blocks is not None or home_blocks is not None:
                blocks_str = f"{away_blocks or 0} - {home_blocks or 0}"
                self.add_detail("Blocked Shots", blocks_str, row)
                row += 1
        
        # Period Scores Section
        periods = self.game.get("periods", [])
        if periods:
            self.add_section_header("Period Breakdown", row)
            row += 1
            
            for period in periods:
                period_num = period.get("period", 0)
                period_type = period.get("periodType", "")
                away_goals = period.get("awayTeam", {}).get("goals", 0)
                home_goals = period.get("homeTeam", {}).get("goals", 0)
                
                period_label = f"Period {period_num}"
                if period_type == "OT":
                    period_label = f"Overtime {period_num}"
                elif period_type == "SO":
                    period_label = "Shootout"
                
                period_score = f"{away_goals} - {home_goals}"
                self.add_detail(period_label, period_score, row)
                row += 1
    
    def add_section_header(self, text, row):
        """Add a section header"""
        header = QLabel(f"<b style='font-size: 14pt; color: #2c3e50;'>{text}</b>")
        header.setStyleSheet("background-color: #e8e8e8; padding: 8px; border-radius: 5px; margin-top: 5px;")
        self.details_grid.addWidget(header, row, 0, 1, 2)
    
    def add_detail(self, label, value, row):
        """Add a detail row to the grid"""
        if not value and value != 0:
            value = "N/A"
        
        label_widget = QLabel(f"<b style='color: #34495e;'>{label}:</b>")
        label_widget.setStyleSheet("padding: 5px;")
        value_widget = QLabel(str(value))
        value_widget.setStyleSheet("padding: 5px; color: #2c3e50;")
        value_widget.setWordWrap(True)
        
        self.details_grid.addWidget(label_widget, row, 0)
        self.details_grid.addWidget(value_widget, row, 1)
    
    def _get_full_team_name(self, team):
        """Build the most descriptive team name available"""
        if not team:
            return ""
        
        for key in ("fullName", "commonName", "teamName"):
            value = team.get(key, {})
            if isinstance(value, dict):
                name_value = value.get("default", "")
                if name_value:
                    return name_value
            elif value:
                return value
        
        place = team.get("placeName", {}).get("default", "")
        nickname = team.get("name", {}).get("default", "")
        
        if place and nickname:
            return f"{place} {nickname}"
        
        return nickname or place or team.get("abbrev", "")
    
    def _team_slug(self, team):
        """Create a TSN-friendly slug for a team"""
        full_name = self._get_full_team_name(team)
        if not full_name:
            return ""
        slug = re.sub(r"[^a-z0-9]+", "-", full_name.lower())
        return slug.strip("-")
    
    def open_moneypuck(self):
        """Open the game preview on moneypuck.com in a web window"""
        if self.game_id:
            url = f"https://moneypuck.com/preview.htm?id={self.game_id}"
            self.moneypuck_window = self.create_web_window("MoneyPuck Preview", url)
            self.moneypuck_window.show()
    
    def open_nhl(self):
        """Open the game on NHL.com in a web window"""
        try:
            # Get team abbreviations
            away_team = self.game.get("awayTeam", {})
            home_team = self.game.get("homeTeam", {})
            
            away_abbrev = away_team.get("abbrev", "").lower()
            home_abbrev = home_team.get("abbrev", "").lower()
            
            # Get game date from startTimeUTC
            start_time = self.game.get("startTimeUTC", "")
            if not start_time:
                return
            
            # Parse the date
            utc_time = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            est_time = utc_time - datetime.timedelta(hours=5)
            game_date = est_time.date()
            
            # Format: year/month/day
            year = game_date.year
            month = game_date.month
            day = game_date.day
            
            # Construct URL: https://www.nhl.com/gamecenter/{away}-vs-{home}/{year}/{month}/{day}/{game_id}
            if away_abbrev and home_abbrev and self.game_id:
                url = f"https://www.nhl.com/gamecenter/{away_abbrev}-vs-{home_abbrev}/{year}/{month}/{day}/{self.game_id}"
                self.nhl_window = self.create_web_window("NHL GameCenter", url)
                self.nhl_window.show()
        except Exception as e:
            print(f"Error opening NHL.com: {e}")
    
    def open_tsn(self):
        """Open the game on TSN.ca in a web window"""
        try:
            away_team = self.game.get("awayTeam", {})
            home_team = self.game.get("homeTeam", {})
            
            away_slug = self._team_slug(away_team)
            home_slug = self._team_slug(home_team)
            
            start_time = self.game.get("startTimeUTC", "")
            if not (start_time and away_slug and home_slug and self.game_id):
                return
            
            utc_time = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            est_time = utc_time - datetime.timedelta(hours=5)
            game_date = est_time.strftime("%Y-%m-%d")
            
            url = f"https://www.tsn.ca/nhl/event/{away_slug}-{home_slug}-{game_date}/{self.game_id}/"
            self.tsn_window = self.create_web_window("TSN Game Details", url)
            self.tsn_window.show()
        except Exception as e:
            print(f"Error opening TSN.ca: {e}")
    
    def open_stream_now(self):
        """Open the NHL.com stream in the default browser (new tab)"""
        try:
            url = "https://thetvapp.to/nhl"
            webbrowser.open_new_tab(url)
        except Exception as e:
            print(f"Error opening NHL Stream: {e}")
    
    def create_web_window(self, title, url):
        """Create a web window with the given title and URL"""
        window = QMainWindow()
        window.setWindowTitle(title)
        window.resize(1000, 700)
        
        central = QWidget()
        window.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        
        web_view = QWebEngineView()
        web_view.load(QUrl(url))
        layout.addWidget(web_view)
        
        return window
    
    def closeEvent(self, event):
        """Stop timer when window closes"""
        if self.update_timer.isActive():
            self.update_timer.stop()
        event.accept()

