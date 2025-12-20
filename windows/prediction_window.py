import datetime
import json
import os
from functools import partial
from collections import defaultdict

from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressDialog,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QAbstractItemView,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from nhlpy import NHLClient
from .game_details_window import GameDetailsWindow


class PredictionWindow(QMainWindow):
    """Standalone window for making daily win/loss picks."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Daily NHL Picks")
        self.resize(820, 540)

        self.client = NHLClient()
        self.prediction_date = datetime.date.today().isoformat()
        self.prediction_file = os.path.join(os.path.expanduser("~"), ".nhl_predictions.json")
        self.games = []
        self.predictions = {}
        self.points = 0

        self.fetch_todays_games_with_loading()
        self.load_predictions()
        self.init_ui()
        self.populate_table()

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
        layout.setContentsMargins(12, 12, 12, 12)

        # Header row with score summary and refresh action
        header_layout = QHBoxLayout()
        self.points_label = QLabel("Today's Points: 0 (0%)")
        self.points_label.setStyleSheet("font-weight: bold;")

        self.total_label = QLabel("Total: 0 pts (0%)")
        self.total_label.setStyleSheet("font-weight: bold; margin-left: 20px;")

        self.instructions_label = QLabel("Pick the winner for each matchup. Earn 1 point for every correct final.")
        self.instructions_label.setStyleSheet("color: #aaaaaa;")

        header_layout.addWidget(self.points_label)
        header_layout.addWidget(self.total_label)
        header_layout.addStretch()
        header_layout.addWidget(self.instructions_label)
        layout.addLayout(header_layout)

        controls = QHBoxLayout()
        controls.addStretch()
        self.refresh_button = QPushButton("Refresh schedule")
        self.refresh_button.clicked.connect(self.refresh_games)
        controls.addWidget(self.refresh_button)

        self.stats_button = QPushButton("View Stats")
        self.stats_button.clicked.connect(self.show_stats_dialog)
        controls.addWidget(self.stats_button)

        layout.addLayout(controls)

        self.table = QTableWidget()
        self.table.setShowGrid(False)
        headers = ["Time (EST)", "Matchup", "Score", "Status", "Venue", "Your Pick", "Confidence", "Result"]
        self.table.setColumnCount(len(headers))
        self.pick_col = headers.index("Your Pick")
        self.conf_col = headers.index("Confidence")
        self.result_col = headers.index("Result")
        for col, text in enumerate(headers):
            self.table.setHorizontalHeaderItem(col, QTableWidgetItem(text))

        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.itemClicked.connect(self.handle_item_click)
        layout.addWidget(self.table)

    def populate_table(self):
        self.table.setRowCount(len(self.games))

        for row, game in enumerate(self.games):
            display = self.build_display_for_game(game)
            for col, item in enumerate(display):
                self.table.setItem(row, col, item)

            matchup_item = display[1]
            game_id = str(game.get("id", ""))
            matchup_item.setData(Qt.ItemDataRole.UserRole, game_id)
            matchup_item.setData(Qt.ItemDataRole.UserRole + 1, row)

            combo = QComboBox()
            away = game.get("awayTeam", {}).get("abbrev", "")
            home = game.get("homeTeam", {}).get("abbrev", "")
            combo.addItem("Select winner", "")
            combo.addItem(f"{away}", away)
            combo.addItem(f"{home}", home)
            pred = self.predictions.get(game_id, {})
            stored_pick = pred.get("pick") if isinstance(pred, dict) else pred
            if stored_pick:
                idx = combo.findData(stored_pick)
                if idx != -1:
                    combo.setCurrentIndex(idx)
            combo.currentIndexChanged.connect(partial(self.handle_pick_change, game_id, row))
            self.table.setCellWidget(row, self.pick_col, combo)

            conf_combo = QComboBox()
            conf_combo.addItem("No conf", None)
            for i in range(1, 6):
                conf_combo.addItem(str(i), i)
            stored_conf = pred.get("confidence") if isinstance(pred, dict) else None
            if stored_conf is not None:
                idx = conf_combo.findData(stored_conf)
                if idx != -1:
                    conf_combo.setCurrentIndex(idx)
            conf_combo.currentIndexChanged.connect(partial(self.handle_conf_change, game_id, row))
            self.table.setCellWidget(row, self.conf_col, conf_combo)

            result_text, result_color = self.get_result_display(game, stored_pick)
            result_item = QTableWidgetItem(result_text)
            result_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if result_color:
                result_item.setForeground(result_color)
            self.table.setItem(row, self.result_col, result_item)

        self.update_points_label()

    def build_display_for_game(self, game):
        start_time = game.get("startTimeUTC", "")
        time_str = ""
        if start_time:
            try:
                utc_time = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                est_time = utc_time - datetime.timedelta(hours=5)
                time_str = est_time.strftime("%I:%M %p").lstrip("0")
            except Exception:
                time_str = "TBD"
        else:
            time_str = "TBD"

        away = game.get("awayTeam", {}).get("abbrev", "")
        home = game.get("homeTeam", {}).get("abbrev", "")
        matchup = f"{away} @ {home}"

        away_score = game.get("awayTeam", {}).get("score", 0)
        home_score = game.get("homeTeam", {}).get("score", 0)
        game_state = game.get("gameState", "")
        game_outcome = game.get("gameOutcome", {})

        has_scores = (
            (away_score is not None and away_score != "" and away_score != 0) or
            (home_score is not None and home_score != "" and home_score != 0)
        )
        has_outcome = bool(game_outcome)

        if game_state == "LIVE":
            score_str = f"{away_score} - {home_score}"
            period_descriptor = game.get("periodDescriptor", {}) or {}
            period = game.get("period")
            if not period:
                for key in ("number", "periodNumber", "period"):
                    value = period_descriptor.get(key)
                    if isinstance(value, int) and value > 0:
                        period = value
                        break
            if not period:
                period = 1
            period_type = period_descriptor.get("periodType", "")
            if period_type == "OT":
                status_str = f"OT {period}"
            elif period_type == "SO":
                status_str = "SO"
            else:
                status_str = f"{period_type or 'Period'} {period}"
        elif game_state in ("FINAL", "OFFICIAL") or has_outcome:
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
            score_str = "VS"
            status_str = "Upcoming"

        venue = game.get("venue", {}).get("default", "TBD")

        items = [
            QTableWidgetItem(time_str),
            QTableWidgetItem(matchup),
            QTableWidgetItem(score_str),
            QTableWidgetItem(status_str),
            QTableWidgetItem(venue),
        ]

        for item in items:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        if game_state in ("FINAL", "OFFICIAL") or has_outcome or (has_scores and game_state == "OFF"):
            for item in items:
                item.setForeground(QColor("lightgreen"))

        return items

    def handle_item_click(self, item):
        if item.column() != 1:
            return
        game_id = item.data(Qt.ItemDataRole.UserRole)
        row = item.data(Qt.ItemDataRole.UserRole + 1)
        if game_id and row is not None and row < len(self.games):
            self.open_game_details(self.games[row])

    def open_game_details(self, game):
        self.details_window = GameDetailsWindow(game, self.client)
        self.details_window.show()

    def refresh_games(self):
        self.fetch_todays_games_with_loading()
        self.populate_table()

    def load_predictions(self):
        try:
            if os.path.exists(self.prediction_file):
                with open(self.prediction_file, "r") as f:
                    data = json.load(f)
                day_data = data.get(self.prediction_date, {})
                raw_predictions = day_data.get("predictions", {})
                self.predictions = {}
                for gid, val in raw_predictions.items():
                    if isinstance(val, str):
                        self.predictions[gid] = {"pick": val, "confidence": None}
                    elif isinstance(val, dict):
                        self.predictions[gid] = val
            else:
                self.predictions = {}
        except Exception:
            self.predictions = {}

    def save_predictions(self):
        try:
            data = {}
            if os.path.exists(self.prediction_file):
                with open(self.prediction_file, "r") as f:
                    data = json.load(f)
            data[self.prediction_date] = {"predictions": self.predictions}
            with open(self.prediction_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def handle_pick_change(self, game_id, row):
        combo = self.sender()
        if combo is None:
            return
        selection = combo.currentData()
        pred = self.predictions.get(game_id, {})
        conf = pred.get("confidence") if isinstance(pred, dict) else None
        if selection:
            self.predictions[game_id] = {"pick": selection, "confidence": conf}
        else:
            self.predictions.pop(game_id, None)
        self.save_predictions()

        if 0 <= row < len(self.games):
            game = self.games[row]
            result_text, result_color = self.get_result_display(game, selection)
            result_item = self.table.item(row, self.result_col)
            if result_item is None:
                result_item = QTableWidgetItem()
                self.table.setItem(row, self.result_col, result_item)
            result_item.setText(result_text)
            result_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if result_color:
                result_item.setForeground(result_color)
            else:
                result_item.setForeground(QColor("white"))

        self.update_points_label()

    def handle_conf_change(self, game_id, row):
        conf_combo = self.sender()
        if conf_combo is None:
            return
        conf = conf_combo.currentData()
        pred = self.predictions.get(game_id, {})
        pick = pred.get("pick") if isinstance(pred, dict) else None
        self.predictions[game_id] = {"pick": pick, "confidence": conf}
        self.save_predictions()

    def determine_winner(self, game):
        game_state = game.get("gameState", "")
        game_outcome = game.get("gameOutcome", {})
        away = game.get("awayTeam", {}).get("abbrev", "")
        home = game.get("homeTeam", {}).get("abbrev", "")
        away_score = game.get("awayTeam", {}).get("score")
        home_score = game.get("homeTeam", {}).get("score")

        has_scores = away_score not in (None, "") and home_score not in (None, "")
        is_final = game_state in ("FINAL", "OFFICIAL") or bool(game_outcome) or (has_scores and game_state == "OFF")
        if not is_final or not has_scores:
            return None

        try:
            away_score = int(away_score)
            home_score = int(home_score)
        except (TypeError, ValueError):
            return None

        if away_score > home_score:
            return away
        if home_score > away_score:
            return home
        return None

    def get_result_display(self, game, pick):
        winner = self.determine_winner(game)
        if not pick:
            return ("No pick", QColor("gray"))
        if not winner:
            return ("Pending", QColor("#f7c948"))
        if pick == winner:
            return ("Correct (+1)", QColor("green"))
        return ("Incorrect", QColor("#ff6666"))

    def calculate_total_stats(self):
        """Calculate total points and percentage across all days."""
        try:
            if not os.path.exists(self.prediction_file):
                return 0, 0, 0
            
            with open(self.prediction_file, "r") as f:
                data = json.load(f)
            
            total_correct = 0
            total_picks = 0
            
            for date_str, day_data in data.items():
                predictions = day_data.get("predictions", {})
                
                # Load games for this date
                try:
                    sched = self.client.schedule.daily_schedule(date=date_str)
                    games = sched.get("games", [])
                except Exception:
                    continue
                
                for game in games:
                    game_id = str(game.get("id", ""))
                    pred = predictions.get(game_id)
                    if isinstance(pred, dict):
                        pick = pred.get("pick")
                    else:
                        pick = pred
                    if not pick:
                        continue
                    
                    total_picks += 1
                    winner = self.determine_winner(game)
                    if winner and winner == pick:
                        total_correct += 1
            
            percentage = (total_correct / total_picks * 100) if total_picks > 0 else 0
            return total_correct, total_picks, percentage
        except Exception:
            return 0, 0, 0

    def get_yesterday_percentage(self):
        """Get yesterday's total percentage for comparison."""
        try:
            yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
            
            if not os.path.exists(self.prediction_file):
                return None
            
            with open(self.prediction_file, "r") as f:
                data = json.load(f)
            
            total_correct = 0
            total_picks = 0
            
            # Calculate up to and including yesterday
            for date_str, day_data in data.items():
                if date_str > yesterday:
                    continue
                    
                predictions = day_data.get("predictions", {})
                
                try:
                    sched = self.client.schedule.daily_schedule(date=date_str)
                    games = sched.get("games", [])
                except Exception:
                    continue
                
                for game in games:
                    game_id = str(game.get("id", ""))
                    pred = predictions.get(game_id)
                    if isinstance(pred, dict):
                        pick = pred.get("pick")
                    else:
                        pick = pred
                    if not pick:
                        continue
                    
                    total_picks += 1
                    winner = self.determine_winner(game)
                    if winner and winner == pick:
                        total_correct += 1
            
            if total_picks == 0:
                return None
            return (total_correct / total_picks * 100)
        except Exception:
            return None

    def update_points_label(self):
        # Today's stats
        today_points = 0
        picked = 0
        finished_picks = 0
        
        for game in self.games:
            game_id = str(game.get("id", ""))
            pred = self.predictions.get(game_id, {})
            pick = pred.get("pick") if isinstance(pred, dict) else pred
            if not pick:
                continue
            picked += 1
            winner = self.determine_winner(game)
            if winner:
                finished_picks += 1
                if winner == pick:
                    today_points += 1
        
        total = len(self.games)
        today_pct = (today_points / finished_picks * 100) if finished_picks > 0 else 0
        
        self.points = today_points
        self.points_label.setText(
            f"Today's Points: {today_points}/{finished_picks} ({today_pct:.0f}%) - picks made {picked}/{total}"
        )
        
        # Total stats with comparison
        total_correct, total_picks, total_pct = self.calculate_total_stats()
        yesterday_pct = self.get_yesterday_percentage()
        
        total_text = f"Total: {total_correct}/{total_picks} ({total_pct:.1f}%)"
        
        # Determine color and tooltip
        if yesterday_pct is not None and total_picks > 0:
            pct_change = total_pct - yesterday_pct
            if abs(pct_change) >= 0.1:  # Only show change if significant
                if pct_change > 0:
                    color = "green"
                    tooltip = f"{yesterday_pct:.1f}% → {total_pct:.1f}%"
                else:
                    color = "red"
                    tooltip = f"{yesterday_pct:.1f}% → {total_pct:.1f}%"
                
                self.total_label.setText(total_text)
                self.total_label.setStyleSheet(f"font-weight: bold; margin-left: 20px; color: {color};")
                self.total_label.setToolTip(tooltip)
            else:
                self.total_label.setText(total_text)
                self.total_label.setStyleSheet("font-weight: bold; margin-left: 20px;")
                self.total_label.setToolTip("")
        else:
            self.total_label.setText(total_text)
            self.total_label.setStyleSheet("font-weight: bold; margin-left: 20px;")
            self.total_label.setToolTip("")

    def get_all_historical_picks(self, include_today=True):
        if not os.path.exists(self.prediction_file):
            return []

        with open(self.prediction_file, "r") as f:
            data = json.load(f)

        all_picks = []

        for date_str, day_data in sorted(data.items(), reverse=True):  # recent first
            if not include_today and date_str == self.prediction_date:
                continue

            try:
                sched = self.client.schedule.daily_schedule(date=date_str)
                games = sched.get("games", [])
            except:
                continue

            for game in games:
                game_id = str(game["id"])
                pred = day_data.get("predictions", {}).get(game_id)
                if not pred:
                    continue

                if isinstance(pred, str):
                    pick = pred
                    conf = None
                else:
                    pick = pred.get("pick")
                    conf = pred.get("confidence")

                if not pick:
                    continue

                start_time = game.get("startTimeUTC", "")
                if start_time:
                    try:
                        utc_time = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    except:
                        utc_time = None
                else:
                    utc_time = None

                winner = self.determine_winner(game)
                is_correct = winner == pick if winner else None

                all_picks.append({
                    "date": date_str,
                    "time": utc_time,
                    "game": game,
                    "pick": pick,
                    "conf": conf,
                    "correct": is_correct
                })

        all_picks.sort(key=lambda x: x["time"] or datetime.datetime.min, reverse=True)
        return all_picks

    def calculate_streak(self):
        picks = self.get_all_historical_picks(include_today=True)
        streak = 0
        for p in picks:
            if p["correct"] is None:
                continue
            if p["correct"]:
                streak += 1
            else:
                break
        return streak

    def calculate_confidence_stats(self):
        picks = self.get_all_historical_picks(include_today=True)
        stats = {i: [0, 0] for i in range(1, 6)}  # correct, total
        for p in picks:
            if p["conf"] is None or p["correct"] is None:
                continue
            stats[p["conf"]][1] += 1
            if p["correct"]:
                stats[p["conf"]][0] += 1
        return stats

    def calculate_monthly_stats(self):
        picks = self.get_all_historical_picks(include_today=True)
        monthly = defaultdict(lambda: [0, 0])  # correct, total
        for p in picks:
            if p["correct"] is None:
                continue
            month = datetime.date.fromisoformat(p["date"]).strftime("%Y-%m")
            monthly[month][1] += 1
            if p["correct"]:
                monthly[month][0] += 1
        result = {}
        for m in sorted(monthly):
            corr, tot = monthly[m]
            pct = corr / tot * 100 if tot else 0
            result[m] = (corr, tot, pct)
        return result

    def get_all_predictions(self):
        picks = self.get_all_historical_picks(include_today=True)
        rows = []
        for p in picks:
            date = p["date"]
            time_str = p["time"].strftime("%I:%M %p").lstrip("0") if p["time"] else "TBD"
            away = p["game"]["awayTeam"]["abbrev"]
            home = p["game"]["homeTeam"]["abbrev"]
            matchup = f"{away} @ {home}"
            pick = p["pick"]
            conf = str(p["conf"]) if p["conf"] else "-"
            if p["correct"] is None:
                result = "Pending"
            elif p["correct"]:
                result = "Correct"
            else:
                result = "Incorrect"
            rows.append([date, time_str, matchup, pick, conf, result])
        return rows

    def show_stats_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Prediction Stats")
        dialog.resize(800, 600)
        layout = QVBoxLayout(dialog)

        tab = QTabWidget()
        layout.addWidget(tab)

        # Overview tab
        overview = QWidget()
        ov_layout = QVBoxLayout(overview)

        # Streak
        streak = self.calculate_streak()
        streak_text = f"Current Streak: {streak} correct in a row 🔥" if streak > 0 else "No current streak"
        ov_layout.addWidget(QLabel(streak_text))

        # Confidence stats
        conf_stats = self.calculate_confidence_stats()
        conf_table = QTableWidget()
        conf_table.setColumnCount(3)
        conf_table.setHorizontalHeaderLabels(["Confidence", "Correct/Total", "Accuracy"])
        conf_table.setRowCount(5)
        for row, conf in enumerate(range(1, 6)):
            correct, total = conf_stats[conf]
            pct = correct / total * 100 if total > 0 else 0
            conf_table.setItem(row, 0, QTableWidgetItem(str(conf)))
            conf_table.setItem(row, 1, QTableWidgetItem(f"{correct}/{total}"))
            conf_table.setItem(row, 2, QTableWidgetItem(f"{pct:.1f}%"))
        ov_layout.addWidget(QLabel("Confidence Accuracy:"))
        ov_layout.addWidget(conf_table)

        # Monthly breakdown
        monthly = self.calculate_monthly_stats()
        month_table = QTableWidget()
        month_table.setColumnCount(3)
        month_table.setHorizontalHeaderLabels(["Month", "Correct/Total", "Percentage"])
        month_table.setRowCount(len(monthly))
        for r, (month, (corr, tot, pct)) in enumerate(sorted(monthly.items())):
            month_table.setItem(r, 0, QTableWidgetItem(month))
            month_table.setItem(r, 1, QTableWidgetItem(f"{corr}/{tot}"))
            month_table.setItem(r, 2, QTableWidgetItem(f"{pct:.1f}%"))
        ov_layout.addWidget(QLabel("Monthly Breakdown:"))
        ov_layout.addWidget(month_table)

        tab.addTab(overview, "Overview")

        # All predictions tab
        all_pred = QWidget()
        ap_layout = QVBoxLayout(all_pred)
        all_table = QTableWidget()
        all_table.setColumnCount(6)
        all_table.setHorizontalHeaderLabels(["Date", "Time", "Matchup", "Pick", "Confidence", "Result"])
        rows = self.get_all_predictions()
        all_table.setRowCount(len(rows))
        for r, row_data in enumerate(rows):
            for c, text in enumerate(row_data):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                all_table.setItem(r, c, item)
        ap_layout.addWidget(all_table)
        tab.addTab(all_pred, "All Predictions")

        dialog.exec()