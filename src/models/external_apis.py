"""Models for external API responses (Golemio, OpenMeteo, Nameday, Todoist)."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from zoneinfo import ZoneInfo

from .enums import WEATHER_DESCRIPTIONS, ApiUrl


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
class OpenMeteoHourly:
    """Hourly series from OpenMeteo API (temperature graph)."""
    time: List[str] = field(default_factory=list)
    temperature_2m: List[float] = field(default_factory=list)
    apparent_temperature: List[float] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OpenMeteoHourly":
        return cls(
            time=data.get("time", []),
            temperature_2m=data.get("temperature_2m", []),
            apparent_temperature=data.get("apparent_temperature", [])
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "time": self.time,
            "temperature_2m": self.temperature_2m,
            "apparent_temperature": self.apparent_temperature
        }


@dataclass
class OpenMeteoResponse:
    """Full response from OpenMeteo API."""
    current: OpenMeteoCurrent
    daily: OpenMeteoDaily
    hourly: OpenMeteoHourly

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OpenMeteoResponse":
        return cls(
            current=OpenMeteoCurrent.from_dict(data.get("current", {})),
            daily=OpenMeteoDaily.from_dict(data.get("daily", {})),
            hourly=OpenMeteoHourly.from_dict(data.get("hourly", {}))
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
            forecast=self.daily.to_dict(),
            hourly=self.hourly.to_dict()
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
            is_completed=data.get("checked", False),
            priority=data.get("priority", 1),
            order=data.get("child_order", 0),
            created_at=data.get("added_at"),
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
            order=data.get("child_order", 0),
            comment_count=0,
            is_shared=data.get("is_shared", False),
            is_favorite=data.get("is_favorite", False),
            is_inbox_project=data.get("inbox_project", False),
            is_team_inbox=False,
            view_style=data.get("view_style", "list"),
            url=None
        )


# ============================================================================
# Google Calendar API Models
# ============================================================================

@dataclass
class GoogleCalendarEventTime:
    """Time data from Google Calendar API event."""
    date_time: Optional[str] = None
    date: Optional[str] = None
    time_zone: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GoogleCalendarEventTime":
        """Parse event time from API response."""
        return cls(
            date_time=data.get("dateTime"),
            date=data.get("date"),
            time_zone=data.get("timeZone")
        )

    def get_value(self) -> str:
        """Get the time value (dateTime or date)."""
        return self.date_time or self.date or ""

    def is_all_day(self) -> bool:
        """Check if this is an all-day event."""
        return self.date is not None and self.date_time is None


@dataclass
class GoogleCalendarEventResponse:
    """Response model for a Google Calendar event from the API."""
    id: str
    summary: str
    start: GoogleCalendarEventTime
    end: GoogleCalendarEventTime
    color_id: Optional[str] = None
    status: str = "confirmed"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GoogleCalendarEventResponse":
        """Parse Google Calendar event from API response."""
        return cls(
            id=data.get("id", ""),
            summary=data.get("summary", "No Title"),
            start=GoogleCalendarEventTime.from_dict(data.get("start", {})),
            end=GoogleCalendarEventTime.from_dict(data.get("end", {})),
            color_id=data.get("colorId"),
            status=data.get("status", "confirmed")
        )

    def to_calendar_event(self, calendar_id: str, calendar_name: str, calendar_color: str | None = None) -> "CalendarEvent":
        """Convert to internal CalendarEvent model with timezone conversion to UTC.

        Uses the dateTime and timeZone fields from the API response to create
        timezone-aware datetimes, then converts to UTC for consistent handling.
        """
        from .internal import CalendarEvent

        is_all_day = self.start.is_all_day()

        # Get timezone from the event (API populates this when we pass timeZone parameter)
        # Default to Europe/Prague if not provided
        event_tz_name = self.start.time_zone or "Europe/Prague"
        event_tz = ZoneInfo(event_tz_name)
        utc_tz = ZoneInfo("UTC")

        if is_all_day:
            # For all-day events, use date field and construct datetime at midnight in event timezone
            start_date_str = self.start.date
            end_date_str = self.end.date

            if start_date_str and end_date_str:
                try:
                    # Parse YYYY-MM-DD date and create datetime at midnight in event timezone
                    start_date = datetime.fromisoformat(start_date_str)
                    end_date = datetime.fromisoformat(end_date_str)

                    # Create datetime at midnight in the event's timezone
                    start_dt = start_date.replace(tzinfo=event_tz)
                    end_dt = end_date.replace(tzinfo=event_tz)

                    # Convert to UTC
                    start_utc = start_dt.astimezone(utc_tz)
                    end_utc = end_dt.astimezone(utc_tz)

                    start_str = start_utc.isoformat()
                    end_str = end_utc.isoformat()
                except (ValueError, AttributeError):
                    # Fallback to original values
                    start_str = start_date_str
                    end_str = end_date_str
            else:
                # Fallback
                start_str = self.start.get_value()
                end_str = self.end.get_value()
        else:
            # For timed events, use dateTime field which already has timezone info
            start_datetime_str = self.start.date_time
            end_datetime_str = self.end.date_time

            if start_datetime_str and end_datetime_str:
                try:
                    # Parse ISO datetime (already has timezone like +01:00)
                    start_dt = datetime.fromisoformat(start_datetime_str)
                    end_dt = datetime.fromisoformat(end_datetime_str)

                    # Convert to UTC
                    start_utc = start_dt.astimezone(utc_tz)
                    end_utc = end_dt.astimezone(utc_tz)

                    start_str = start_utc.isoformat()
                    end_str = end_utc.isoformat()
                except (ValueError, AttributeError):
                    # Fallback to original values
                    start_str = start_datetime_str
                    end_str = end_datetime_str
            else:
                # Fallback
                start_str = self.start.get_value()
                end_str = self.end.get_value()

        return CalendarEvent(
            id=self.id,
            summary=self.summary,
            start=start_str,
            end=end_str,
            all_day=is_all_day,
            calendar_id=calendar_id,
            calendar_name=calendar_name,
            color_id=self.color_id,
            calendar_color=calendar_color
        )


# ============================================================================
# NHL tile parsing (unofficial api-web.nhle.com)
# ============================================================================

def _nhl_text(value: Any) -> str:
    """NHL API strings are usually {"default": "..."}; accept plain strings too."""
    if isinstance(value, dict):
        return value.get("default", "") or ""
    return value or ""


def _nhl_period_label(period_descriptor: Dict[str, Any]) -> str:
    """Short period label: P1..P3, OT (2OT, 3OT in the playoffs), SO."""
    period_type = period_descriptor.get("periodType", "REG")
    number = period_descriptor.get("number", 0) or 0
    if period_type == "SO":
        return "SO"
    if period_type == "OT":
        return "OT" if number <= 4 else f"{number - 3}OT"
    return f"P{number}"


def _nhl_series_text(status: Dict[str, Any]) -> Optional[str]:
    """Series state from the score feed's seriesStatus, e.g. "BOS leads 3–1"."""
    top, bottom = status.get("topSeedTeamAbbrev"), status.get("bottomSeedTeamAbbrev")
    if not top or not bottom:
        return None
    top_wins = status.get("topSeedWins", 0) or 0
    bottom_wins = status.get("bottomSeedWins", 0) or 0
    needed = status.get("neededToWin", 4) or 4
    if top_wins >= needed:
        return f"{top} wins series {top_wins}–{bottom_wins}"
    if bottom_wins >= needed:
        return f"{bottom} wins series {bottom_wins}–{top_wins}"
    if top_wins == bottom_wins:
        return f"Series tied {top_wins}–{bottom_wins}"
    leader, hi, lo = (top, top_wins, bottom_wins) if top_wins > bottom_wins else (bottom, bottom_wins, top_wins)
    return f"{leader} leads {hi}–{lo}"


def _nhl_score_team(team: Dict[str, Any]) -> "NhlScoreTeam":
    from .internal import NhlScoreTeam
    return NhlScoreTeam(
        abbrev=team.get("abbrev", "?"),
        name=_nhl_text(team.get("name")),
        score=team.get("score"),
        sog=team.get("sog"),
    )


def _nhl_decider(game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Find the goal that decided a finished game.

    For regulation/OT games that's the game-winning goal: the winner's goal that
    took them one past the loser's final score. Shootout games are decided by
    the shootout winner (the feed lists it as a goal with periodType "SO").
    """
    if game.get("gameState") not in ("OFF", "FINAL"):
        return None
    away_final = (game.get("awayTeam") or {}).get("score")
    home_final = (game.get("homeTeam") or {}).get("score")
    if away_final is None or home_final is None or away_final == home_final:
        return None

    goals = game.get("goals", [])
    shootout = [g for g in goals if (g.get("periodDescriptor") or {}).get("periodType") == "SO"]
    if shootout:
        return shootout[-1]

    home_won = home_final > away_final
    winner = (game.get("homeTeam") if home_won else game.get("awayTeam")) or {}
    target = min(away_final, home_final) + 1
    for goal in goals:
        if _nhl_text(goal.get("teamAbbrev")) != winner.get("abbrev"):
            continue
        if goal.get("homeScore" if home_won else "awayScore") == target:
            return goal
    return None


def parse_nhl_score_games(data: Dict[str, Any]) -> List["NhlScoreGame"]:
    """Parse the /v1/score/{date} response into scoreboard games, earliest first."""
    from .internal import NhlScoreGame

    games: List["NhlScoreGame"] = []
    for g in data.get("games", []):
        descriptor = g.get("periodDescriptor") or {}
        outcome = g.get("gameOutcome") or {}
        clock = g.get("clock") or {}

        series = g.get("seriesStatus") or {}
        decider = _nhl_decider(g)
        decider_when = None
        if decider:
            label = _nhl_period_label(decider.get("periodDescriptor") or {})
            decider_when = label if label == "SO" else f"{label} {decider.get('timeInPeriod', '')}".strip()

        games.append(NhlScoreGame(
            id=g.get("id", 0),
            state=g.get("gameState", "FUT"),
            schedule_state=g.get("gameScheduleState", "OK"),
            start_utc=g.get("startTimeUTC", ""),
            away=_nhl_score_team(g.get("awayTeam") or {}),
            home=_nhl_score_team(g.get("homeTeam") or {}),
            period=g.get("period") or descriptor.get("number") or 0,
            period_type=outcome.get("lastPeriodType") or descriptor.get("periodType") or "REG",
            clock=clock.get("timeRemaining", "") or "",
            in_intermission=bool(clock.get("inIntermission")),
            game_type=g.get("gameType", 2) or 2,
            series_letter=series.get("seriesLetter"),
            series_game=series.get("gameNumberOfSeries"),
            series_status=_nhl_series_text(series) if series else None,
            decider=_nhl_text(decider.get("name")) if decider else None,
            decider_team=_nhl_text(decider.get("teamAbbrev")) if decider else None,
            decider_when=decider_when,
        ))

    games.sort(key=lambda x: (x.start_utc, x.id))
    return games


def parse_nhl_standings(data: Dict[str, Any]) -> List["NhlStanding"]:
    """Parse /v1/standings/now into rows ordered by division, then division rank."""
    from .internal import NhlStanding

    rows: List["NhlStanding"] = []
    for r in data.get("standings", []):
        streak_code = r.get("streakCode") or ""
        rows.append(NhlStanding(
            abbrev=_nhl_text(r.get("teamAbbrev")),
            place=_nhl_text(r.get("placeName")),
            name=_nhl_text(r.get("teamCommonName")),
            conference=r.get("conferenceName", ""),
            division=r.get("divisionName", ""),
            games_played=r.get("gamesPlayed", 0) or 0,
            wins=r.get("wins", 0) or 0,
            losses=r.get("losses", 0) or 0,
            ot_losses=r.get("otLosses", 0) or 0,
            points=r.get("points", 0) or 0,
            point_pct=round(r.get("pointPctg", 0.0) or 0.0, 3),
            goal_diff=r.get("goalDifferential", 0) or 0,
            l10=f"{r.get('l10Wins', 0)}-{r.get('l10Losses', 0)}-{r.get('l10OtLosses', 0)}",
            streak=f"{streak_code}{r.get('streakCount', 0)}" if streak_code else "",
            division_rank=r.get("divisionSequence", 0) or 0,
            conference_rank=r.get("conferenceSequence", 0) or 0,
            league_rank=r.get("leagueSequence", 0) or 0,
            wildcard_rank=r.get("wildcardSequence", 0) or 0,
            clinch=r.get("clinchIndicator") or None,
        ))

    rows.sort(key=lambda s: (s.conference, s.division, s.division_rank))
    return rows


def parse_nhl_leaders(data: Dict[str, Any], categories: List[Tuple[str, str]]) -> List["NhlLeaderBoard"]:
    """Parse a skater/goalie stats-leaders response into ordered leader boards."""
    from .internal import NhlLeader, NhlLeaderBoard

    boards: List["NhlLeaderBoard"] = []
    for key, label in categories:
        leaders = [
            NhlLeader(
                player_id=p.get("id", 0),
                first_name=_nhl_text(p.get("firstName")),
                last_name=_nhl_text(p.get("lastName")),
                team=_nhl_text(p.get("teamAbbrev")),
                headshot=p.get("headshot", ""),
                number=p.get("sweaterNumber"),
                position=p.get("position", ""),
                value=float(p.get("value") or 0),
            )
            for p in data.get(key, [])
        ]
        boards.append(NhlLeaderBoard(category=key, label=label, leaders=leaders))
    return boards


def parse_nhl_bracket(data: Dict[str, Any]) -> Optional["NhlBracket"]:
    """
    Parse /v1/playoff-bracket/{year}. Returns None until the playoffs have matchups.

    Stage = the earliest round that still has an undecided series (1-4), or 5
    once the Stanley Cup Final is won. Between rounds it points at the next one.
    """
    from .internal import NhlBracket, NhlBracketSeries, NhlBracketTeam

    def team(raw: Dict[str, Any], seed: Optional[str], wins: Optional[int]) -> Optional["NhlBracketTeam"]:
        if not raw.get("abbrev"):
            return None
        return NhlBracketTeam(
            abbrev=raw["abbrev"],
            name=_nhl_text(raw.get("commonName")),
            seed=seed or "",
            wins=wins or 0,
        )

    series_list: List["NhlBracketSeries"] = []
    for s in data.get("series", []):
        top_raw = s.get("topSeedTeam") or {}
        bottom_raw = s.get("bottomSeedTeam") or {}
        winner_id = s.get("winningTeamId")
        winner = None
        if winner_id:
            if top_raw.get("id") == winner_id:
                winner = top_raw.get("abbrev")
            elif bottom_raw.get("id") == winner_id:
                winner = bottom_raw.get("abbrev")
        series_list.append(NhlBracketSeries(
            letter=s.get("seriesLetter", ""),
            round=s.get("playoffRound", 0) or 0,
            title=s.get("seriesTitle", ""),
            top=team(top_raw, s.get("topSeedRankAbbrev"), s.get("topSeedWins")),
            bottom=team(bottom_raw, s.get("bottomSeedRankAbbrev"), s.get("bottomSeedWins")),
            winner=winner,
        ))

    if not any(x.top or x.bottom for x in series_list):
        return None

    series_list.sort(key=lambda x: x.letter)
    final = next((x for x in series_list if x.round == 4), None)
    undecided = [x.round for x in series_list if x.top and x.bottom and not x.winner]
    if undecided:
        stage = min(undecided)
    elif final and final.winner:
        stage = 5
    else:
        stage = min(4, max(x.round for x in series_list) + 1)

    return NhlBracket(
        stage=stage,
        series=series_list,
        champion=final.winner if final and final.winner else None,
    )
