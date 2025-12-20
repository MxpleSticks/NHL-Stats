# Import all window classes from separate modules for backward compatibility
from .past_games_window import PastGamesWindow
from .upcoming_window import UpcomingWindow
from .todays_games_window import TodaysGamesWindow
from .game_details_window import GameDetailsWindow

# Re-export for backward compatibility
__all__ = ['PastGamesWindow', 'UpcomingWindow', 'TodaysGamesWindow', 'GameDetailsWindow']
