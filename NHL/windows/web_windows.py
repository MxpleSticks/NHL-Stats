from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView


class GoaliesWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Predicted Goalies")
        self.resize(1000, 700)
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView()
        self.web_view.load(QUrl("https://www.rotowire.com/hockey/starting-goalies.php"))
        layout.addWidget(self.web_view)


class LineupsWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Predicted Lineups")
        self.resize(1000, 700)
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView()
        self.web_view.load(QUrl("https://www.rotowire.com/hockey/nhl-lineups.php"))
        layout.addWidget(self.web_view)


class PlayoffWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NHL Playoff Probabilities")
        self.resize(1000, 700)
        self.init_ui()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView()
        self.web_view.load(QUrl("https://moneypuck.com/predictions.htm"))
        layout.addWidget(self.web_view)


class TeamLinesWindow(QMainWindow):
    def __init__(self, url):
        super().__init__()
        self.setWindowTitle("Team Line Combinations")
        self.resize(1000, 700)
        self.init_ui(url)

    def init_ui(self, url):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView()
        self.web_view.load(QUrl(url))
        layout.addWidget(self.web_view)

