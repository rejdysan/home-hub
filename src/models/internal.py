"""Internal application models."""
from dataclasses import dataclass, field, asdict, replace
from typing import Dict, Any, Optional, List


@dataclass
class FrontendConfig:
    """Configuration values sent to the frontend."""
    google_maps_update_interval: int  # in milliseconds
    google_calendar_update_interval: int  # in milliseconds
    morning_mode_start: int
    day_mode_start: int
    night_mode_start: int
    nhl_tile_rotate_interval: int = 10000  # in milliseconds

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SystemStats:
    """System resource statistics."""
    cpu: float
    ram_pct: float
    ram_used: float
    ram_total: float
    disk_pct: float
    disk_used: float
    disk_total: float
    net_sent: float
    net_recv: float
    cpu_temp: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def empty(cls) -> "SystemStats":
        return cls(
            cpu=0.0, ram_pct=0.0, ram_used=0.0, ram_total=0.0,
            disk_pct=0.0, disk_used=0.0, disk_total=0.0,
            net_sent=0.0, net_recv=0.0, cpu_temp=None
        )


@dataclass
class SensorStatus:
    """Online/offline status for a single sensor."""
    online: bool
    last_seen: float
    seconds_ago: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SensorReading:
    """A sensor reading from the database."""
    sensor: str
    prop: str
    temp: float
    ts: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SystemHealth:
    """Represents system health status."""
    mqtt: bool
    database: bool
    wifi: bool


@dataclass
class BusDeparture:
    """Represents a single bus departure."""
    line: str
    direction: str
    mins: int
    time_scheduled: str
    time_predicted: str
    delay_minutes: int
    delay_seconds: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BusDepartures:
    """Container for bus departures from multiple stops."""
    malesicka: List[BusDeparture] = field(default_factory=list)
    olgy: List[BusDeparture] = field(default_factory=list)

    def to_dict(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "malesicka": [dep.to_dict() for dep in self.malesicka],
            "olgy": [dep.to_dict() for dep in self.olgy]
        }

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BusDepartures):
            return False
        return self.malesicka == other.malesicka and self.olgy == other.olgy


@dataclass
class CurrentWeather:
    """Represents current weather data."""
    updated: str
    temp: int
    feels: int
    is_day: bool
    code: int
    desc: str
    wind: int
    hum: int
    pres: int
    vis: int
    uv: int
    cloud: int
    forecast: Dict[str, Any]
    hourly: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def equals_ignoring_updated(self, other: "CurrentWeather") -> bool:
        """Compare weather data ignoring the updated timestamp."""
        return (
                self.temp == other.temp and
                self.feels == other.feels and
                self.is_day == other.is_day and
                self.code == other.code and
                self.desc == other.desc and
                self.wind == other.wind and
                self.hum == other.hum and
                self.pres == other.pres and
                self.vis == other.vis and
                self.uv == other.uv and
                self.cloud == other.cloud and
                self.forecast == other.forecast and
                self.hourly == other.hourly
        )


@dataclass
class TodoistTask:
    """Represents a single Todoist task."""
    id: str
    content: str
    is_completed: bool
    priority: int
    order: int
    project_id: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TodoistProject:
    """Represents a Todoist project with its tasks."""
    id: str
    name: str
    tasks: List[TodoistTask] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "tasks": [task.to_dict() for task in self.tasks]
        }


@dataclass
class TodoistData:
    """Container for Todoist projects."""
    projects: List[TodoistProject] = field(default_factory=list)

    def to_dict(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "projects": [project.to_dict() for project in self.projects]
        }

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TodoistData):
            return False
        return self.projects == other.projects


@dataclass
class CalendarEvent:
    """Represents a single Google Calendar event."""
    id: str
    summary: str
    start: str
    end: str
    all_day: bool
    calendar_id: str
    calendar_name: str
    color_id: Optional[str] = None
    calendar_color: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CalendarData:
    """Container for calendar events."""
    events: List[CalendarEvent] = field(default_factory=list)
    updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "events": [event.to_dict() for event in self.events],
            "updated": self.updated
        }

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CalendarData):
            return False
        return self.events == other.events


# ============================================================================
# NHL tile models (scores, standings, bracket, leaders)
# ============================================================================

@dataclass
class NhlScoreTeam:
    """One side of a game on the scoreboard."""
    abbrev: str
    name: str                      # common name, e.g. "Canadiens"
    score: Optional[int] = None
    sog: Optional[int] = None      # shots on goal


@dataclass
class NhlScoreGame:
    """A single game from the daily scoreboard (finished, live or upcoming)."""
    id: int
    state: str                     # FUT, PRE, LIVE, CRIT, FINAL, OFF
    schedule_state: str            # OK, PPD (postponed), CNCL, ...
    start_utc: str
    away: NhlScoreTeam
    home: NhlScoreTeam
    period: int = 0
    period_type: str = "REG"       # REG / OT / SO (current, or how a final ended)
    clock: str = ""                # time remaining in the period, e.g. "12:34"
    in_intermission: bool = False
    game_type: int = 2             # NhlGameType: 1 preseason, 2 regular, 3 playoffs
    # Playoff games only
    series_letter: Optional[str] = None
    series_game: Optional[int] = None    # game number within the series
    series_status: Optional[str] = None  # e.g. "BOS leads 3–1" (after this game, once final)
    # Game-deciding goal (the "highlight" line under a finished game)
    decider: Optional[str] = None  # scorer, e.g. "C. Caufield"
    decider_team: Optional[str] = None
    decider_when: Optional[str] = None  # e.g. "OT 00:30", "P3 07:14", "SO"


@dataclass
class NhlStanding:
    """One team's row in the league standings."""
    abbrev: str
    place: str                     # e.g. "Carolina"
    name: str                      # common name, e.g. "Hurricanes"
    conference: str
    division: str
    games_played: int
    wins: int
    losses: int
    ot_losses: int
    points: int
    point_pct: float
    goal_diff: int
    l10: str                       # last 10 record, e.g. "7-2-1"
    streak: str                    # e.g. "W3"
    division_rank: int
    conference_rank: int
    league_rank: int
    wildcard_rank: int             # 1/2 = holds a wild card, 0 = division spot
    clinch: Optional[str] = None   # x / y / z / p / e when decided


@dataclass
class NhlLeader:
    """A player on a stats leader board."""
    player_id: int
    first_name: str
    last_name: str
    team: str
    headshot: str
    number: Optional[int]
    position: str
    value: float


@dataclass
class NhlLeaderBoard:
    """Top players for one stat category (e.g. points)."""
    category: str                  # API key, e.g. "savePctg"
    label: str                     # display label, e.g. "Save %"
    leaders: List[NhlLeader] = field(default_factory=list)


@dataclass
class NhlBracketTeam:
    """A team in a playoff bracket series."""
    abbrev: str
    name: str                      # common name, e.g. "Hurricanes"
    seed: str                      # e.g. "D1", "WC2"
    wins: int = 0


@dataclass
class NhlBracketSeries:
    """One playoff series. Letters: A-D East R1, E-H West R1, I-J East R2,
    K-L West R2, M East final, N West final, O Stanley Cup Final."""
    letter: str
    round: int                     # 1-4
    title: str                     # e.g. "1st Round", "Stanley Cup Final"
    top: Optional[NhlBracketTeam] = None
    bottom: Optional[NhlBracketTeam] = None
    winner: Optional[str] = None   # abbrev of the series winner
    needed_to_win: int = 4


@dataclass
class NhlBracket:
    """The playoff tree and how far it has progressed."""
    stage: int                     # 1-4 = round in progress, 5 = Cup decided
    series: List[NhlBracketSeries] = field(default_factory=list)
    champion: Optional[str] = None


@dataclass
class NhlLeague:
    """Everything the rotating NHL tile shows."""
    season: str = ""               # e.g. "20262027"
    phase: str = "regular"         # NhlPhase
    bracket: Optional[NhlBracket] = None
    results_date: str = ""         # NHL game date of "last night"
    results: List[NhlScoreGame] = field(default_factory=list)
    upcoming_date: str = ""        # NHL game date of "tonight"
    upcoming: List[NhlScoreGame] = field(default_factory=list)
    standings: List[NhlStanding] = field(default_factory=list)
    skater_leaders: List[NhlLeaderBoard] = field(default_factory=list)
    goalie_leaders: List[NhlLeaderBoard] = field(default_factory=list)
    updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def has_live_games(self) -> bool:
        """True while any game on either scoreboard is in progress."""
        return any(g.state in ("LIVE", "CRIT") for g in self.results + self.upcoming)

    def equals_ignoring_updated(self, other: "NhlLeague") -> bool:
        """Compare league data ignoring the updated timestamp."""
        if not isinstance(other, NhlLeague):
            return False
        return replace(self, updated="") == replace(other, updated="")
