"""Models for external API responses (Golemio, OpenMeteo, Nameday, Todoist)."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List

from .enums import WEATHER_DESCRIPTIONS


@dataclass
class GolemioTimestamp:
    """Timestamp data from Golemio API."""
    predicted: Optional[str] = None
    scheduled: Optional[str] = None
    minutes: Optional[str] = None  # Can be "<1", "7", etc.

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GolemioTimestamp":
        return cls(
            predicted=data.get("predicted"),
            scheduled=data.get("scheduled"),
            minutes=data.get("minutes")
        )

    def get_minutes_int(self) -> int:
        """Convert minutes string to int, handling '<1' case."""
        if self.minutes is None:
            return 0
        if self.minutes == "<1":
            return 0
        try:
            return int(self.minutes)
        except ValueError:
            return 0

    def format_time(self) -> str:
        """Extract HH:MM:SS from ISO timestamp."""
        ts = self.predicted or self.scheduled
        if ts:
            try:
                dt = datetime.fromisoformat(ts)
                return dt.strftime("%H:%M:%S")
            except ValueError:
                pass
        return "--:--:--"


@dataclass
class GolemioDelay:
    """Delay information from Golemio API."""
    is_available: bool = False
    minutes: int = 0
    seconds: int = 0

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "GolemioDelay":
        if not data:
            return cls()
        return cls(
            is_available=data.get("is_available", False),
            minutes=data.get("minutes", 0),
            seconds=data.get("seconds", 0)
        )


@dataclass
class GolemioRoute:
    """Route information from Golemio API."""
    short_name: str
    type: int = 3
    is_night: bool = False
    is_regional: bool = False
    is_substitute_transport: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GolemioRoute":
        return cls(
            short_name=data.get("short_name", ""),
            type=data.get("type", 3),
            is_night=data.get("is_night", False),
            is_regional=data.get("is_regional", False),
            is_substitute_transport=data.get("is_substitute_transport", False)
        )


@dataclass
class GolemioStop:
    """Stop information from Golemio API."""
    id: str
    platform_code: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GolemioStop":
        return cls(
            id=data.get("id", ""),
            platform_code=data.get("platform_code")
        )


@dataclass
class GolemioTrip:
    """Trip information from Golemio API."""
    headsign: str
    id: str
    direction: Optional[str] = None
    is_at_stop: bool = False
    is_canceled: bool = False
    is_wheelchair_accessible: bool = False
    is_air_conditioned: bool = False
    short_name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GolemioTrip":
        return cls(
            headsign=data.get("headsign", ""),
            id=data.get("id", ""),
            direction=data.get("direction"),
            is_at_stop=data.get("is_at_stop", False),
            is_canceled=data.get("is_canceled", False),
            is_wheelchair_accessible=data.get("is_wheelchair_accessible", False),
            is_air_conditioned=data.get("is_air_conditioned", False),
            short_name=data.get("short_name")
        )


@dataclass
class GolemioDeparture:
    """A single departure from Golemio API."""
    arrival_timestamp: GolemioTimestamp
    departure_timestamp: GolemioTimestamp
    delay: GolemioDelay
    route: GolemioRoute
    stop: GolemioStop
    trip: GolemioTrip

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GolemioDeparture":
        return cls(
            arrival_timestamp=GolemioTimestamp.from_dict(data.get("arrival_timestamp", {})),
            departure_timestamp=GolemioTimestamp.from_dict(data.get("departure_timestamp", {})),
            delay=GolemioDelay.from_dict(data.get("delay")),
            route=GolemioRoute.from_dict(data.get("route", {})),
            stop=GolemioStop.from_dict(data.get("stop", {})),
            trip=GolemioTrip.from_dict(data.get("trip", {}))
        )

    def to_bus_departure(self) -> "BusDeparture":
        """Convert to our internal BusDeparture model."""
        from .internal import BusDeparture
        return BusDeparture(
            line=self.route.short_name,
            direction=self.trip.headsign,
            mins=self.departure_timestamp.get_minutes_int(),
            time_scheduled=GolemioTimestamp(scheduled=self.departure_timestamp.scheduled).format_time(),
            time_predicted=self.departure_timestamp.format_time(),
            delay_minutes=self.delay.minutes,
            delay_seconds=self.delay.seconds
        )


@dataclass
class GolemioResponse:
    """Full response from Golemio departures API."""
    departures: List[GolemioDeparture] = field(default_factory=list)
    infotexts: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GolemioResponse":
        departures = [
            GolemioDeparture.from_dict(dep)
            for dep in data.get("departures", [])
        ]
        return cls(
            departures=departures,
            infotexts=data.get("infotexts", [])
        )


@dataclass
class NamedayResponse:
    """Response from nameday.abalin.net API."""
    country: str
    nameday: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any], country: str = "sk") -> "NamedayResponse":
        return cls(
            country=country,
            nameday=data.get("data", {}).get(country, "Unknown")
        )


@dataclass
class OpenMeteoCurrent:
    """Current weather data from OpenMeteo API."""
    temperature_2m: float
    apparent_temperature: float
    is_day: int
    weather_code: int
    wind_speed_10m: float
    relative_humidity_2m: int
    pressure_msl: float
    uv_index: float
    cloud_cover: int
    visibility: float

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OpenMeteoCurrent":
        return cls(
            temperature_2m=data.get("temperature_2m", 0.0),
            apparent_temperature=data.get("apparent_temperature", 0.0),
            is_day=data.get("is_day", 0),
            weather_code=data.get("weather_code", 0),
            wind_speed_10m=data.get("wind_speed_10m", 0.0),
            relative_humidity_2m=data.get("relative_humidity_2m", 0),
            pressure_msl=data.get("pressure_msl", 0.0),
            uv_index=data.get("uv_index", 0.0),
            cloud_cover=data.get("cloud_cover", 0),
            visibility=data.get("visibility", 0.0)
        )


@dataclass
class OpenMeteoDaily:
    """Daily forecast data from OpenMeteo API."""
    time: List[str] = field(default_factory=list)
    temperature_2m_max: List[float] = field(default_factory=list)
    temperature_2m_min: List[float] = field(default_factory=list)
    weather_code: List[int] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OpenMeteoDaily":
        return cls(
            time=data.get("time", []),
            temperature_2m_max=data.get("temperature_2m_max", []),
            temperature_2m_min=data.get("temperature_2m_min", []),
            weather_code=data.get("weather_code", [])
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "time": self.time,
            "temperature_2m_max": self.temperature_2m_max,
            "temperature_2m_min": self.temperature_2m_min,
            "weather_code": self.weather_code
        }


@dataclass
class OpenMeteoResponse:
    """Full response from OpenMeteo API."""
    current: OpenMeteoCurrent
    daily: OpenMeteoDaily

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OpenMeteoResponse":
        return cls(
            current=OpenMeteoCurrent.from_dict(data.get("current", {})),
            daily=OpenMeteoDaily.from_dict(data.get("daily", {}))
        )

    def to_current_weather(self) -> "CurrentWeather":
        """Convert to our internal CurrentWeather model."""
        import datetime
        from .internal import CurrentWeather

        now = datetime.datetime.now().strftime("%H:%M:%S")

        return CurrentWeather(
            updated=now,
            temp=round(self.current.temperature_2m),
            feels=round(self.current.apparent_temperature),
            is_day=self.current.is_day == 1,
            code=self.current.weather_code,
            desc=WEATHER_DESCRIPTIONS.get(self.current.weather_code, "Cloudy"),
            wind=round(self.current.wind_speed_10m),
            hum=self.current.relative_humidity_2m,
            pres=round(self.current.pressure_msl),
            vis=round(self.current.visibility / 1000),
            uv=round(self.current.uv_index),
            cloud=self.current.cloud_cover,
            forecast=self.daily.to_dict()
        )


# ============================================================================
# Todoist API Models
# ============================================================================

@dataclass
class TodoistTaskResponse:
    """Response model for a Todoist task from the API."""
    id: str
    content: str
    project_id: str
    is_completed: bool
    priority: int
    order: int
    created_at: Optional[str] = None
    due: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TodoistTaskResponse":
        """Parse Todoist task from API response."""
        return cls(
            id=str(data.get("id", "")),
            content=data.get("content", ""),
            project_id=str(data.get("project_id", "")),
            is_completed=data.get("is_completed", False),
            priority=data.get("priority", 1),
            order=data.get("order", 0),
            created_at=data.get("created_at"),
            due=data.get("due")
        )

    def to_todoist_task(self) -> "TodoistTask":
        """Convert to internal TodoistTask model."""
        from .internal import TodoistTask
        return TodoistTask(
            id=self.id,
            content=self.content,
            is_completed=self.is_completed,
            priority=self.priority,
            order=self.order,
            project_id=self.project_id
        )


@dataclass
class TodoistProjectResponse:
    """Response model for a Todoist project from the API."""
    id: str
    name: str
    color: Optional[str] = None
    parent_id: Optional[str] = None
    order: int = 0
    comment_count: int = 0
    is_shared: bool = False
    is_favorite: bool = False
    is_inbox_project: bool = False
    is_team_inbox: bool = False
    view_style: str = "list"
    url: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TodoistProjectResponse":
        """Parse Todoist project from API response."""
        return cls(
            id=str(data.get("id", "")),
            name=data.get("name", ""),
            color=data.get("color"),
            parent_id=str(data["parent_id"]) if data.get("parent_id") else None,
            order=data.get("order", 0),
            comment_count=data.get("comment_count", 0),
            is_shared=data.get("is_shared", False),
            is_favorite=data.get("is_favorite", False),
            is_inbox_project=data.get("is_inbox_project", False),
            is_team_inbox=data.get("is_team_inbox", False),
            view_style=data.get("view_style", "list"),
            url=data.get("url")
        )
