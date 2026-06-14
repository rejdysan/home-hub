"""Internal application models."""
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List


@dataclass
class FrontendConfig:
    """Configuration values sent to the frontend."""
    google_maps_update_interval: int  # in milliseconds
    google_calendar_update_interval: int  # in milliseconds
    morning_mode_start: int
    day_mode_start: int
    night_mode_start: int

    def to_dict(self) -> Dict[str, int]:
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
# NHL Stanley Cup Final models
# ============================================================================

@dataclass
class NhlTeam:
    """One team in an NHL playoff series."""
    abbrev: str
    place: str
    name: str
    wins: int
    logo: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NhlGame:
    """One game within an NHL playoff series."""
    number: int
    state: str          # OFF (final), LIVE, FUT (future), PRE
    away: str           # team abbrev
    home: str           # team abbrev
    away_score: Optional[int] = None
    home_score: Optional[int] = None
    winner: Optional[str] = None   # abbrev of winning team, if decided
    start_utc: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NhlSeries:
    """A playoff series (used for the Stanley Cup Final panel)."""
    round_label: str
    needed_to_win: int
    top: NhlTeam
    bottom: NhlTeam
    games: List[NhlGame] = field(default_factory=list)
    updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round_label": self.round_label,
            "needed_to_win": self.needed_to_win,
            "top": self.top.to_dict(),
            "bottom": self.bottom.to_dict(),
            "games": [g.to_dict() for g in self.games],
            "updated": self.updated,
        }

    def equals_ignoring_updated(self, other: "NhlSeries") -> bool:
        """Compare series data ignoring the updated timestamp."""
        if not isinstance(other, NhlSeries):
            return False
        return (
            self.round_label == other.round_label and
            self.needed_to_win == other.needed_to_win and
            self.top == other.top and
            self.bottom == other.bottom and
            self.games == other.games
        )

