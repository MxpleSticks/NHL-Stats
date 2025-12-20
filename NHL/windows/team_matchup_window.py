import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QAbstractItemView,
    QProgressDialog, QApplication
)
from PyQt6.QtCore import Qt
from nhlpy import NHLClient


class TeamMatchupWindow(QDialog):
    """Predict which team has the edge by comparing standings stats and H2H results."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.client = NHLClient()
        self.setWindowTitle("Team Matchup Predictor")
        self.resize(920, 640)

        self.team_lookup = self.build_team_lookup()
        self.schedule_cache = {}
        self.stats_definitions = [
            ("Points", "points"),
            ("Point %", "pointPctg"),
            ("Goal Diff", "goalDifferential"),
            ("Goals For", "goalFor"),
            ("Goals Against", "goalAgainst"),
            ("Wins", "wins"),
            ("Reg+OT Wins", "regulationPlusOtWins"),
            ("Streak", ("streakCode", "streakCount")),
        ]

        self.init_ui()

    def build_team_lookup(self):
        """Build a lookup from abbreviation to the team dictionary and keep ranking order."""
        lookup = {}
        self.team_order = []
        teams = getattr(self.parent, "standings", []) or []
        for team in teams:
            abbrev = team.get("teamAbbrev", {}).get("default", "")
            if not abbrev:
                continue
            lookup[abbrev] = team
            self.team_order.append(team)

        self.team_order.sort(key=lambda t: t.get("leagueSequence", 999))
        return lookup

    def init_ui(self):
        layout = QVBoxLayout(self)

        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("Team 1"))
        self.team1_combo = QComboBox()
        self.team1_combo.setToolTip("Pick the first team to compare")
        control_layout.addWidget(self.team1_combo)

        control_layout.addWidget(QLabel("Team 2"))
        self.team2_combo = QComboBox()
        self.team2_combo.setToolTip("Pick the second team to compare")
        control_layout.addWidget(self.team2_combo)

        swap_button = QPushButton("Swap Teams")
        swap_button.clicked.connect(self.swap_teams)
        control_layout.addWidget(swap_button)

        layout.addLayout(control_layout)

        self.populate_team_options()

        self.prediction_label = QLabel("Pick two different teams to get a prediction.")
        self.prediction_label.setWordWrap(True)
        self.prediction_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.prediction_label)

        self.stats_table = QTableWidget(len(self.stats_definitions), 3)
        self.stats_table.setHorizontalHeaderLabels(["Stat", "Team 1", "Team 2"])
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.stats_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.stats_table)

        self.head_to_head_summary = QLabel("Head-to-head details appear here.")
        self.head_to_head_summary.setStyleSheet("padding-top: 10px; font-style: italic;")
        layout.addWidget(self.head_to_head_summary)

        self.head_to_head_table = QTableWidget(0, 5)
        headers = ["Date", "Location", "Result", "Score", "Notes"]
        self.head_to_head_table.setHorizontalHeaderLabels(headers)
        self.head_to_head_table.verticalHeader().setVisible(False)
        self.head_to_head_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.head_to_head_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.head_to_head_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.head_to_head_table)

        self.team1_combo.currentIndexChanged.connect(self.update_comparison)
        self.team2_combo.currentIndexChanged.connect(self.update_comparison)

        self.update_comparison()

    def populate_team_options(self):
        """Fill the combo boxes with current standings order."""
        for combo in (self.team1_combo, self.team2_combo):
            combo.clear()
        for team in self.team_order:
            abbrev = team.get("teamAbbrev", {}).get("default", "")
            name = team.get("teamName", {}).get("default", "")
            label = f"{abbrev} — {name}"
            self.team1_combo.addItem(label, abbrev)
            self.team2_combo.addItem(label, abbrev)
        if self.team2_combo.count() > 1:
            self.team2_combo.setCurrentIndex(1)

    def swap_teams(self):
        """Switch the selected teams to see the matchup from the other side."""
        idx1 = self.team1_combo.currentIndex()
        idx2 = self.team2_combo.currentIndex()
        if idx1 >= 0 and idx2 >= 0:
            self.team1_combo.setCurrentIndex(idx2)
            self.team2_combo.setCurrentIndex(idx1)

    def update_comparison(self):
        """Refresh stats comparison, prediction, and head-to-head data."""
        team1_abbrev = self.team1_combo.currentData()
        team2_abbrev = self.team2_combo.currentData()
        team1 = self.team_lookup.get(team1_abbrev, {})
        team2 = self.team_lookup.get(team2_abbrev, {})

        team1_label = self.get_combo_label(team1, team1_abbrev)
        team2_label = self.get_combo_label(team2, team2_abbrev)
        self.stats_table.setHorizontalHeaderLabels(["Stat", team1_label, team2_label])

        for row, (label, key) in enumerate(self.stats_definitions):
            self.stats_table.setItem(row, 0, self.make_item(label, align=Qt.AlignmentFlag.AlignLeft))
            self.stats_table.setItem(row, 1, self.make_item(self.format_stat(key, team1)))
            self.stats_table.setItem(row, 2, self.make_item(self.format_stat(key, team2)))

        if not team1_abbrev or not team2_abbrev or team1_abbrev == team2_abbrev:
            self.prediction_label.setText("Choose two different teams to show a matchup prediction.")
            self.head_to_head_summary.setText("")
            self.head_to_head_table.setRowCount(0)
            return

        h2h = self.get_head_to_head_games(team1_abbrev, team2_abbrev)
        team1_strength = self.calculate_strength(team1) + (h2h["team1_wins"] * 1.4)
        team2_strength = self.calculate_strength(team2) + (h2h["team2_wins"] * 1.4)
        self.set_prediction_label(team1_label, team2_label, team1_strength, team2_strength)

        self.head_to_head_summary.setText(h2h["summary"])
        self.populate_head_to_head_table(h2h["games"])

    def set_prediction_label(self, team1_label, team2_label, score1, score2):
        diff = abs(score1 - score2)
        if diff < 0.75:
            text = f"Expected to be very close: {team1_label} ({score1:.1f}) vs {team2_label} ({score2:.1f})."
        else:
            favorite = team1_label if score1 > score2 else team2_label
            text = f"{favorite} holds the edge ({score1:.1f} vs {score2:.1f}, diff {diff:.1f})."
        self.prediction_label.setText(text)

    def populate_head_to_head_table(self, games):
        self.head_to_head_table.setRowCount(len(games))
        for row, entry in enumerate(games):
            items = [
                self.make_item(entry["date"]),
                self.make_item(entry["location"]),
                self.make_item(entry["result"]),
                self.make_item(entry["score"]),
                self.make_item(entry["notes"] or "—"),
            ]
            for col, item in enumerate(items):
                self.head_to_head_table.setItem(row, col, item)

    def format_stat(self, key, team):
        value = None
        if isinstance(key, tuple):
            code, count = key
            ticker = team.get(code, "")
            amount = team.get(count, 0)
            if amount:
                return f"{ticker}{amount}"
            return ticker or "—"

        if key == "pointPctg":
            value = self.safe_float(team.get(key))
            return f"{value:.3f}"

        value = team.get(key, "")
        if value is None or value == "":
            return "—"
        return str(value)

    def make_item(self, text, align=Qt.AlignmentFlag.AlignCenter):
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(align)
        return item

    def get_combo_label(self, team, abbrev):
        if not team and not abbrev:
            return "Team"
        full_name = team.get("teamName", {}).get("default", "") or team.get("teamAbbrev", {}).get("default", abbrev)
        return f"{abbrev} {full_name}".strip()

    def calculate_strength(self, team):
        # Weighted sum of key stats to help pick a projected winner.
        multipliers = [
            (1.3, "points"),
            (0.7, "goalDifferential"),
            (0.4, "pointPctg"),
            (0.35, "wins"),
            (0.5, "regulationPlusOtWins"),
            (-0.25, "goalAgainst"),
        ]
        total = 0.0
        for weight, key in multipliers:
            total += weight * self.safe_float(team.get(key))
        return total

    def safe_float(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def get_head_to_head_games(self, team1_abbrev, team2_abbrev):
        games = []

        # Show a small loading dialog when pulling a team's season schedule,
        # since this can take a few seconds the first time.
        progress = QProgressDialog(
            f"Loading schedule for {team1_abbrev}...", None, 0, 0, self
        )
        progress.setWindowTitle("Please wait")
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setAutoClose(True)
        progress.setAutoReset(True)
        progress.setMinimumDuration(0)
        progress.setStyleSheet("QLabel { font-family: Consolas, 'Courier New', monospace; }")

        spinner = "|/-\\"
        spinner_index = 0
        spin_char = spinner[spinner_index % len(spinner)]
        progress.setLabelText(f"{spin_char} Loading schedule for {team1_abbrev}...")
        progress.show()
        QApplication.processEvents()

        team_schedule = self.get_team_schedule(team1_abbrev)

        # Nudge the spinner once more so it visually "moves" at least one step
        spinner_index += 1
        spin_char = spinner[spinner_index % len(spinner)]
        progress.setLabelText(f"{spin_char} Loading schedule for {team1_abbrev}...")
        QApplication.processEvents()

        progress.close()
        for game in team_schedule:
            home = game.get("homeTeam", {}).get("abbrev", "")
            away = game.get("awayTeam", {}).get("abbrev", "")
            if {home, away} != {team1_abbrev, team2_abbrev}:
                continue

            home_score = game.get("homeTeam", {}).get("score")
            away_score = game.get("awayTeam", {}).get("score")
            if home_score is None or away_score is None:
                continue

            team1_is_home = home == team1_abbrev
            team1_score = home_score if team1_is_home else away_score
            opponent_score = away_score if team1_is_home else home_score
            last_period_type = game.get("gameOutcome", {}).get("lastPeriodType", "")
            note = "OT" if last_period_type == "OT" else ("SO" if last_period_type == "SO" else "")

            result = "W" if team1_score > opponent_score else "L"
            games.append({
                "date": game.get("gameDate", ""),
                "location": "Home" if team1_is_home else "Away",
                "result": result,
                "score": f"{team1_score} – {opponent_score}",
                "notes": note,
            })

        games_sorted = sorted(games, key=lambda g: g["date"], reverse=True)
        team1_wins = sum(1 for g in games_sorted if g["result"] == "W")
        team2_wins = sum(1 for g in games_sorted if g["result"] == "L")
        if games_sorted:
            summary = (
                f"{team1_abbrev} has beaten {team2_abbrev} {team1_wins} times "
                f"this season (versus {team2_wins} losses)."
            )
        else:
            summary = f"No head-to-head games between {team1_abbrev} and {team2_abbrev} yet."

        return {"games": games_sorted, "summary": summary, "team1_wins": team1_wins, "team2_wins": team2_wins}

    def get_team_schedule(self, team_abbrev):
        if team_abbrev in self.schedule_cache:
            return self.schedule_cache[team_abbrev]
        season = self.get_current_season()
        try:
            schedule = self.client.schedule.team_season_schedule(team_abbr=team_abbrev, season=season)
            games = schedule.get("games", [])
        except Exception:
            games = []
        self.schedule_cache[team_abbrev] = games
        return games

    def get_current_season(self):
        today = datetime.date.today()
        if today.month >= 10:
            start_year = today.year
        else:
            start_year = today.year - 1
        return f"{start_year}{start_year + 1}"

