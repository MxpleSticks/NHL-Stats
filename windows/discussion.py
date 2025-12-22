import webbrowser
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QScrollArea, QGridLayout, QTabWidget, QFrame, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class DiscussionWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Discussions & Resources")
        self.resize(1000, 800)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # Title
        title = QLabel("Community Discussions & Analysis")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        title.setFont(font)
        main_layout.addWidget(title)

        # Tabs
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Team Subreddits
        self.team_tab = QWidget()
        self.setup_team_tab()
        self.tabs.addTab(self.team_tab, "Reddit Communities")

        # Tab 2: Commentators/YouTube
        self.commentator_tab = QWidget()
        self.setup_commentator_tab()
        self.tabs.addTab(self.commentator_tab, "Commentators & Analysts")

        # Tab 3: News & Stats
        self.resources_tab = QWidget()
        self.setup_resources_tab()
        self.tabs.addTab(self.resources_tab, "Resources")

        # Tab 4: Fan Zone
        self.fan_zone_tab = QWidget()
        self.setup_fan_zone_tab()
        self.tabs.addTab(self.fan_zone_tab, "Fan Zone")

        # Close Button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        main_layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def create_button_grid(self, layout, items_dict, columns=4, show_rating=True):
        """Helper to create a grid of buttons from a dictionary with ratings
        items_dict format: {name: (url, rating)}
        """
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(10)

        # Sort by rating (highest to lowest), then by name
        sorted_items = sorted(items_dict.items(), key=lambda x: (-x[1][1], x[0]))

        row = 0
        col = 0
        
        for name, (url, rating) in sorted_items:
            # Construct button text: Include rating inside the button if enabled
            button_text = f"{name} ({rating}/5)" if show_rating else name
            
            # Create button
            btn = QPushButton(button_text)
            btn.clicked.connect(lambda checked, u=url: webbrowser.open(u))
            btn.setMinimumHeight(45) 
            
            # Make text slightly smaller if it's long
            if len(button_text) > 22:
                font = btn.font()
                font.setPointSize(9)
                btn.setFont(font)
            
            grid.addWidget(btn, row, col)

            col += 1
            if col >= columns:
                col = 0
                row += 1
        
        layout.addWidget(grid_widget)

    def setup_team_tab(self):
        layout = QVBoxLayout(self.team_tab)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        # --- Section 1: General Hockey Reddit (Ratings included) ---
        general_group = QGroupBox("General Discussions")
        general_layout = QVBoxLayout()
        general_communities = {
            "r/Hockey": ("https://www.reddit.com/r/hockey/", 5),
            "r/FantasyHockey": ("https://www.reddit.com/r/fantasyhockey/", 5),
            "r/NHL": ("https://www.reddit.com/r/nhl/", 5),
            "r/HockeyJerseys": ("https://www.reddit.com/r/hockeyjerseys/", 5),
        }
        self.create_button_grid(general_layout, general_communities, columns=2, show_rating=True)
        general_group.setLayout(general_layout)
        content_layout.addWidget(general_group)

        # --- Section 2: Team Subreddits (No ratings) ---
        team_group = QGroupBox("Team Communities")
        team_layout = QVBoxLayout()
        
        teams = {
            "Blackhawks": ("https://www.reddit.com/r/hawks/", 5),
            "Leafs": ("https://www.reddit.com/r/leafs/", 5),
            "Red Wings": ("https://www.reddit.com/r/DetroitRedWings/", 5),
            "Bruins": ("https://www.reddit.com/r/BostonBruins/", 5),
            "Penguins": ("https://www.reddit.com/r/penguins/", 5),
            "Flyers": ("https://www.reddit.com/r/Flyers/", 5),
            "Rangers": ("https://www.reddit.com/r/rangers/", 5),
            "Canadiens": ("https://www.reddit.com/r/Habs/", 5),
            "Canucks": ("https://www.reddit.com/r/canucks/", 5),
            "Oilers": ("https://www.reddit.com/r/EdmontonOilers/", 5),
            "Avalanche": ("https://www.reddit.com/r/ColoradoAvalanche/", 5),
            "Lightning": ("https://www.reddit.com/r/TampaBayLightning/", 5),
            "Capitals": ("https://www.reddit.com/r/caps/", 5),
            "Kings": ("https://www.reddit.com/r/losangeleskings/", 5),
            "Hurricanes": ("https://www.reddit.com/r/canes/", 5),
            "Stars": ("https://www.reddit.com/r/DallasStars/", 5),
            "Devils": ("https://www.reddit.com/r/devils/", 5),
            "Wild": ("https://www.reddit.com/r/wildhockey/", 5),
            "Flames": ("https://www.reddit.com/r/calgaryflames/", 5),
            "Jets": ("https://www.reddit.com/r/winnipegjets/", 5),
            "Senators": ("https://www.reddit.com/r/OttawaSenators/", 5),
            "Sharks": ("https://www.reddit.com/r/SanJoseSharks/", 5),
            "Sabres": ("https://www.reddit.com/r/sabres/", 5),
            "Golden Knights": ("https://www.reddit.com/r/goldenknights/", 5),
            "Kraken": ("https://www.reddit.com/r/SeattleKraken/", 5),
            "Blues": ("https://www.reddit.com/r/stlouisblues/", 5),
            "Ducks": ("https://www.reddit.com/r/AnaheimDucks/", 5),
            "Islanders": ("https://www.reddit.com/r/NewYorkIslanders/", 5),
            "Predators": ("https://www.reddit.com/r/Predators/", 5),
            "Panthers": ("https://www.reddit.com/r/FloridaPanthers/", 5),
            "Blue Jackets": ("https://www.reddit.com/r/BlueJackets/", 5),
            "Utah HC": ("https://www.reddit.com/r/Utah_Hockey/", 5)
        }
        self.create_button_grid(team_layout, teams, columns=4, show_rating=False)
        team_group.setLayout(team_layout)
        content_layout.addWidget(team_group)

        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

    def setup_commentator_tab(self):
        layout = QVBoxLayout(self.commentator_tab)
        
        info_label = QLabel("Expert Analysis & Fan Channels")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)

        # --- Section 1: League-Wide Analysts (Ratings included) ---
        general_group = QGroupBox("League-Wide Analysts")
        general_layout = QVBoxLayout()
        general_analysts = {
            "The Hockey Guy": ("https://www.youtube.com/c/TheHockeyGuy", 5),
            "Sportsnet (32 Thoughts)": ("https://www.youtube.com/user/SPORTSNETCANADA", 4),
            "OhNyquist": ("https://www.youtube.com/@OhNyquist", 5),
            "Eck": ("https://www.youtube.com/@Eckh", 5)
        }
        self.create_button_grid(general_layout, general_analysts, columns=2, show_rating=True)
        general_group.setLayout(general_layout)
        content_layout.addWidget(general_group)

        # --- Section 2: Team Specific Coverage (No ratings) ---
        team_group = QGroupBox("Team-Specific Coverage")
        team_layout = QVBoxLayout()
        team_channels = {
            "TOR: Steve Dangle": ("https://www.youtube.com/@SteveDangle", 5),
            "COL: DNVR Avalanche": ("https://www.youtube.com/@DNVR_Sports", 5),
            "CHI: CHGO Blackhawks": ("https://www.youtube.com/@CHGOSports", 5),
            "PHI: PHLY Flyers": ("https://www.youtube.com/@PHLY_Sports", 5),
            "BOS: Locked On Bruins": ("https://www.youtube.com/@LockedOnBruins", 5),
            "DET: Winged Wheel": ("https://www.youtube.com/@WingedWheelPodcast", 5),
            "EDM: Locked On Oilers": ("https://www.youtube.com/@LockedOnOilers", 5),
            "VAN: Locked On Canucks": ("https://www.youtube.com/@LockedOnCanucks", 5),
            "NYR: Locked On Rangers": ("https://www.youtube.com/@LockedOnRangers", 5),
            "PIT: Locked On Penguins": ("https://www.youtube.com/@LockedOnPenguins", 5),
            "MTL: Locked On Canadiens": ("https://www.youtube.com/@LockedOnCanadiens", 5),
            "CAR: Locked On Hurricanes": ("https://www.youtube.com/@LockedOnCanes", 5),
            "ANA: Locked On Ducks": ("https://www.youtube.com/@LockedOnDucks", 5),
            "BUF: Locked On Sabres": ("https://www.youtube.com/@LockedOnSabres", 5),
            "CGY: Locked On Flames": ("https://www.youtube.com/@LockedOnFlames", 5),
            "CBJ: Locked On Blue Jackets": ("https://www.youtube.com/@LockedOnBlueJackets", 5),
            "DAL: Locked On Stars": ("https://www.youtube.com/@LockedOnStars", 5),
            "FLA: Locked On Panthers": ("https://www.youtube.com/@LockedOnPanthers", 5),
            "LAK: Locked On Kings": ("https://www.youtube.com/@LockedOnKings", 5),
            "MIN: Locked On Wild": ("https://www.youtube.com/@LockedOnWild", 5),
            "NSH: Locked On Predators": ("https://www.youtube.com/@LockedOnPreds", 5),
            "NJD: Locked On Devils": ("https://www.youtube.com/@LockedOnDevils", 5),
            "NYI: Locked On Islanders": ("https://www.youtube.com/@LockedOnIslanders", 5),
            "OTT: Locked On Senators": ("https://www.youtube.com/@LockedOnSenators", 5),
            "SJS: Locked On Sharks": ("https://www.youtube.com/@LockedOnSharks", 5),
            "SEA: Locked On Kraken": ("https://www.youtube.com/@LockedOnKraken", 5),
            "STL: Locked On Blues": ("https://www.youtube.com/@LockedOnBlues", 5),
            "TBL: Locked On Lightning": ("https://www.youtube.com/@LockedOnLightning", 5),
            "VGK: Locked On Golden Knights": ("https://www.youtube.com/@LockedOnGoldenKnights", 5),
            "WSH: Locked On Capitals": ("https://www.youtube.com/@LockedOnCapitals", 5),
            "WPG: Locked On Jets": ("https://www.youtube.com/@LockedOnJets", 5),
            "UTA: Locked On Utah HC": ("https://www.youtube.com/@LockedOnMammoth", 5)
        }
        self.create_button_grid(team_layout, team_channels, columns=4, show_rating=False)
        team_group.setLayout(team_layout)
        content_layout.addWidget(team_group)

        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

    def setup_resources_tab(self):
        layout = QVBoxLayout(self.resources_tab)
        
        info_label = QLabel("League Resources & Tools")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)

        sections = [
            ("News & Rumors", {
                "NHL.com": ("https://www.nhl.com/", 5),
                "TSN NHL": ("https://www.tsn.ca/nhl", 5),
                "Sportsnet": ("https://www.sportsnet.ca/nhl/", 5),
                "The Fourth Period": ("https://www.thefourthperiod.com/", 4),
                "Spectors Hockey": ("https://spectorshockey.net/", 3)
            }, 3),
            ("Stats & Analytics", {
                "Hockey Reference": ("https://www.hockey-reference.com/", 5),
                "Natural Stat Trick": ("https://www.naturalstattrick.com/", 5),
                "Moneypuck": ("https://www.moneypuck.com/", 4),
                "Evolving Hockey": ("https://evolving-hockey.com/", 4),
                "HockeyViz": ("https://hockeyviz.com/", 3)
            }, 3),
            ("Salary Cap & Fantasy", {
                "PuckPedia": ("https://puckpedia.com/", 5),
                "Daily Faceoff": ("https://www.dailyfaceoff.com/", 5),
                "Spotrac": ("https://www.spotrac.com/nhl/", 4),
                "Left Wing Lock": ("https://leftwinglock.com/", 4),
                "Dobber Hockey": ("https://dobberhockey.com/", 4)
            }, 3)
        ]

        for title, items, cols in sections:
            group = QGroupBox(title)
            g_layout = QVBoxLayout()
            self.create_button_grid(g_layout, items, columns=cols, show_rating=True)
            group.setLayout(g_layout)
            content_layout.addWidget(group)

        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

    def setup_fan_zone_tab(self):
        layout = QVBoxLayout(self.fan_zone_tab)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)

        # --- Section 1: Collectors & Gear (Ratings included) ---
        merch_group = QGroupBox("Collectors & Gear")
        merch_layout = QVBoxLayout()
        merch_links = {
            "Hockey Authentic": ("https://hockeyauthentic.com/", 5),
            "MeiGray": ("https://meigray.com/", 5),
            "Fanatics": ("https://www.fanatics.com/nhl/", 3),
            "NHL Shop": ("https://shop.nhl.com/", 3)
        }
        self.create_button_grid(merch_layout, merch_links, columns=2, show_rating=True)
        merch_group.setLayout(merch_layout)
        content_layout.addWidget(merch_group)


        # --- Section 2: Tickets & Travel (Ratings included) ---
        ticket_group = QGroupBox("Tickets & Travel Exchanges")
        ticket_layout = QVBoxLayout()
        ticket_links = {
            "TickPick": ("https://www.tickpick.com/nhl-tickets/", 3),
            "Gametime": ("https://gametime.co/nhl-tickets", 4),
            "SeatGeek": ("https://seatgeek.com/nhl-tickets", 5),
            "StubHub": ("https://www.stubhub.com/nhl-tickets/", 4),
            "Ticketmaster": ("https://www.ticketmaster.com/nhl", 5)
        }
        self.create_button_grid(ticket_layout, ticket_links, columns=3, show_rating=True)
        ticket_group.setLayout(ticket_layout)
        content_layout.addWidget(ticket_group)

        # --- Section 3: Official Team Stores (No ratings) ---
        store_group = QGroupBox("Official Team Stores")
        store_layout = QVBoxLayout()
        store_links = {
            # Canadian Teams (Independent where available)
            "TOR: Real Sports": ("https://shop.realsports.ca/", 5),  # Maple Leafs 🇨🇦 :contentReference[oaicite:2]{index=2}
            "VAN: Vanbase": ("https://vanbase.ca/", 4),              # Canucks :contentReference[oaicite:3]{index=3}
            "MTL: Tricolore Sports": ("https://www.tricoloresports.com/", 4),  # Canadiens :contentReference[oaicite:4]{index=4}
            
            # U.S. Teams with independent stores
            "BOS: Boston ProShop": ("https://bostonproshop.com/", 5),           # Bruins :contentReference[oaicite:5]{index=5}
            "VGK: The Arsenal": ("https://vegasteamstore.com/", 4),             # Golden Knights :contentReference[oaicite:6]{index=6}
            "FLA: FLA Team Shop": ("https://flateamshop.com/", 4),              # Panthers :contentReference[oaicite:7]{index=7}
            "CAR: Carolina Pro Shop": ("https://www.carolinaproshop.com/", 4),  # Hurricanes :contentReference[oaicite:8]{index=8}
            "CHI: CBH Shop": ("https://www.cbhshop.com/", 4),                    # Blackhawks :contentReference[oaicite:9]{index=9}
            "COL: Altitude Authentics": ("https://altitudeauthentics.com/", 4), # Avalanche :contentReference[oaicite:10]{index=10}
            "CBJ: Blue Line Online": ("https://thebluelineonline.com/", 4),      # Blue Jackets :contentReference[oaicite:11]{index=11}
            "DAL: Hangar Hockey": ("https://hangarhockey.com/", 4),             # Stars :contentReference[oaicite:12]{index=12}
            "DET: HockeyTown Authentics": ("https://www.shophockeytown.com/", 4),# Red Wings :contentReference[oaicite:13]{index=13}
            "EDM: ICE District Authentics": ("https://www.icedistrictauthentics.com/", 4), # Oilers :contentReference[oaicite:14]{index=14}
            "LAK: Team LA Store": ("https://teamlastore.com/pages/la-kings", 4),# Kings :contentReference[oaicite:15]{index=15}
            "MIN: The Hockey Lodge": ("https://www.hockeylodge.com/", 4),       # Wild :contentReference[oaicite:16]{index=16}
            "NSH: Nashville Locker Room": ("https://nashvillelockerroom.com/", 4), # Predators :contentReference[oaicite:17]{index=17}
            "PIT: PensGear": ("https://pensgear.com/", 4),                      # Penguins :contentReference[oaicite:18]{index=18}
            "SJS: Sharks Pro Shop": ("https://sharksproshop.com/", 4),          # Sharks :contentReference[oaicite:19]{index=19}
            "SEA: Seattle Hockey Team Store": ("https://seattlehockeyteamstore.com/", 4), # Kraken :contentReference[oaicite:20]{index=20}
            "TBL: Tampa Bay Sports": ("https://tampabaysports.com/", 4),        # Lightning :contentReference[oaicite:21]{index=21}
            "WPG: True North Shop": ("https://truenorthshop.com/", 4),          # Jets :contentReference[oaicite:22]{index=22}
            "WSH: Monumental Sports Network Shop": ("https://shop.monumentalsportsnetwork.com/", 5),

            # Teams WITHOUT independent stores → link to league store
            "NYR: Rangers (NHL Shop)": ("https://shop.nhl.com/new-york-rangers/t-36373004+z-9999451-2213146187?_ref=m-TOPNAV", 5),   # Rangers :contentReference[oaicite:23]{index=23}
            "PHI: Flyers (NHL Shop)": ("https://shop.nhl.com/philadelphia-flyers/t-25824141+z-9137121-2666524178?_ref=m-TOPNAV", 4), # Flyers :contentReference[oaicite:24]{index=24}
            "BUF: Sabres (NHL Shop)": ("https://shop.nhl.com/buffalo-sabres/t-36263831+z-9415589-604969543?_ref=m-TOPNAV", 4),     # Sabres :contentReference[oaicite:25]{index=25}
            "NJD: Devils (NHL Shop)": ("https://shop.nhl.com/new-jersey-devils/t-47045202+z-9102782-511447169?_ref=m-TOPNAV", 4),   # Devils :contentReference[oaicite:26]{index=26}
            "NYI: Islanders (NHL Shop)": ("https://shop.nhl.com/new-york-islanders/t-14154103+z-9121312-2914045911?_ref=m-TOPNAV", 4),# Islanders :contentReference[oaicite:27]{index=27}
            "OTT: Senators (NHL Shop)": ("https://shop.nhl.com/ottawa-senators/t-47040751+z-9317806-3207036255?_ref=m-TOPNAV", 4),   # Senators :contentReference[oaicite:28]{index=28}
            "STL: Blues (NHL Shop)": ("https://shop.nhl.com/st-louis-blues/t-47482012+z-848003-4097081403?_ref=m-TOPNAV", 4),       # Blues :contentReference[oaicite:29]{index=29}
        }
        self.create_button_grid(store_layout, store_links, columns=3, show_rating=False)
        store_group.setLayout(store_layout)
        content_layout.addWidget(store_group)

        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)