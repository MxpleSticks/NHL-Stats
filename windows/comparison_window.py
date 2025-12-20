import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QSpinBox, QHBoxLayout,
    QPushButton, QCalendarWidget
)
from nhlpy import NHLClient


class ComparisonWindow(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Compare Standings")
        self.resize(400, 300)
        self.parent_window = parent
        self.client = NHLClient()

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Add label and spinbox for days ago
        label = QLabel("Compare to standings from:")
        layout.addWidget(label)

        spinbox_layout = QHBoxLayout()
        spinbox_label = QLabel("Days ago:")
        self.days_spinbox = QSpinBox()
        self.days_spinbox.setMinimum(1)
        self.days_spinbox.setMaximum(365)
        self.days_spinbox.setValue(2)
        self.days_spinbox.valueChanged.connect(self.update_calendar_from_spinbox)
        spinbox_layout.addWidget(spinbox_label)
        spinbox_layout.addWidget(self.days_spinbox)
        spinbox_layout.addStretch()
        layout.addLayout(spinbox_layout)

        # Add calendar option
        cal_label = QLabel("Or select a specific date:")
        layout.addWidget(cal_label)

        self.calendar = QCalendarWidget()
        self.calendar.setSelectedDate(datetime.date.today() - datetime.timedelta(days=2))
        self.calendar.selectionChanged.connect(self.update_spinbox_from_calendar)
        layout.addWidget(self.calendar)

        # Button layout
        button_layout = QHBoxLayout()

        compare_button = QPushButton("Compare")
        compare_button.clicked.connect(self.compare)
        button_layout.addWidget(compare_button)

        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(self.reset)
        button_layout.addWidget(reset_button)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def update_calendar_from_spinbox(self):
        """Update calendar when spinbox changes"""
        days_ago = self.days_spinbox.value()
        new_date = datetime.date.today() - datetime.timedelta(days=days_ago)
        self.calendar.blockSignals(True)  # Prevent recursive update
        self.calendar.setSelectedDate(new_date)
        self.calendar.blockSignals(False)

    def update_spinbox_from_calendar(self):
        """Update spinbox when calendar changes"""
        selected_date = self.calendar.selectedDate().toPyDate()
        days_ago = (datetime.date.today() - selected_date).days
        if 1 <= days_ago <= 365:
            self.days_spinbox.blockSignals(True)  # Prevent recursive update
            self.days_spinbox.setValue(days_ago)
            self.days_spinbox.blockSignals(False)

    def compare(self):
        # Use the spinbox value (days ago)
        selected_date = (datetime.date.today() - datetime.timedelta(days=self.days_spinbox.value())).isoformat()
        try:
            comparison_data = self.client.standings.league_standings(date=selected_date)["standings"]
            comparison_ranks = {team["teamAbbrev"]["default"]: team["leagueSequence"] for team in comparison_data}
            comparison_stats = {team["teamAbbrev"]["default"]: team for team in comparison_data}
            self.parent_window.set_comparison_date(comparison_ranks, comparison_stats)
            self.close()
        except Exception as e:
            print(f"Error fetching data for {selected_date}: {e}")

    def reset(self):
        self.parent_window.reset_comparison()
        self.close()

