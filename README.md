# NHL Stats

A comprehensive PyQt6-based desktop application for tracking NHL standings, games, and statistics with real-time updates.

## Video Demo

[![NHL Stats Demo](https://img.youtube.com/vi/vzVyN5AOvEU/maxresdefault.jpg)](https://youtu.be/vzVyN5AOvEU)

**[Watch the full demo on YouTube](https://youtu.be/vzVyN5AOvEU)**

## Features

- **Live Standings**: View current NHL standings with sortable columns and team comparisons
- **Today's Games**: Real-time scoreboard with live updates and game status
- **Upcoming & Past Games**: Browse future matchups and historical results
- **Game Details**: In-depth game statistics, period breakdowns, and live updates
- **Team Matchup Predictor**: Compare teams head-to-head with strength analysis
- **Daily Picks**: Make game predictions and track your accuracy over time
- **Favorite Teams**: Star your favorite teams for highlighted tracking with rainbow effects
- **Advanced Statistics**: Toggle between basic and advanced stats mode
- **External Links**: Quick access to MoneyPuck, NHL.com, TSN, and streaming sites
- **Playoff Tracker**: See which teams would make playoffs if the season ended today

## Installation

### Option 1: Windows Executable (No Python Required)

Download a pre-built Windows executable from the **Releases** page:
- Download **NHL-Stats.exe**
- No Python or dependencies required
- Just run the executable to start the app

### Option 2: Run from Source (All Platforms)

#### Requirements
- Python 3.8 or higher
- pip (Python package installer)

#### Required Libraries
- **PyQt6** (>=6.0.0): Main GUI framework
- **PyQt6-WebEngine** (>=6.0.0): For embedded web views (game details, external sites)
- **nhlpy** (>=0.5.0): NHL API client for fetching game data and standings

#### Installation Steps

1. **Clone or download this repository**
```bash
   git clone https://github.com/MxpleSticks/NHL-Stats.git
   cd NHL-Stats
```

2. **Install dependencies**
   
   Using requirements.txt (recommended):
```bash
   pip install -r requirements.txt
```
   
   Or install manually:
```bash
   pip install PyQt6 PyQt6-WebEngine nhlpy
```

3. **Run the application**
```bash
   python main.py
```

## Usage

### Main Window
- Click on team names to view line combinations
- Click on rank to toggle favorite teams (shows ★)
- Click on "Last" column to view a team's most recent game
- Use the scrolling ticker at the top to quickly see today's games
- Click any game in the ticker to open detailed information

### Sorting
- Click column headers to sort (click again to reverse, third click to reset)
- Supports multi-level sorting for records (W-L-OT)

### Comparisons
- Click "Compare" to compare current standings with a past date
- Green/red arrows show rank improvements/declines
- Stats are color-coded to show improvements (green) or declines (red)

### Favorites
- Click the rank column to star/unstar teams
- Favorite teams are highlighted with a white border
- Winning games for favorites show rainbow colors
- Favorites are saved between sessions

### Game Details
- Click matchups in any view to open detailed game information
- Live games auto-refresh every 5 seconds
- Access external sites (MoneyPuck, NHL.com, TSN) with one click

### Daily Picks
- Make predictions for each game's winner
- Assign confidence levels (1-5) to your picks
- Track your accuracy over time with detailed statistics
- View monthly breakdown and current winning streak

### Discussion/Resources
- LINKS for days

## Data Storage

The app stores user data in your home directory:
- **Favorites**: `~/.nhl_favorites.json`
- **Predictions**: `~/.nhl_predictions.json`

## Known Issues

- **Windows 10 Theme Compatibility**: UI rendering may look slightly different on Windows 10 due to theme compatibility. All functionality works correctly. This is a known limitation of PyQt6 cross-version compatibility.
- Requires active internet connection for live data
- API rate limits may apply during heavy usage
- Historical data fetching can take 10-30 seconds for full season

## Project Status

This project is **feature complete**. Only critical bug fixes will be released. Feature requests will not be accepted at this time.

## Troubleshooting

### "No module named 'PyQt6'"
Install PyQt6: `pip install PyQt6 PyQt6-WebEngine`

### "No module named 'nhlpy'"
Install nhlpy: `pip install nhlpy`

### Games not loading
Check your internet connection and verify the NHL API is accessible

### Web views not displaying
Ensure PyQt6-WebEngine is properly installed: `pip install PyQt6-WebEngine`

## Credits

- **NHL API**: Data provided by the official NHL API
- **nhlpy**: Python wrapper for NHL API by [@coreyjs](https://github.com/coreyjs/nhlpy)
- **External Sites**: MoneyPuck, NHL.com, TSN, RotoWire, DailyFaceoff

## License

This project is for personal use only. NHL data and trademarks are property of the National Hockey League.

## Version

Current Version: 1.1.0
