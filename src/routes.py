import asyncio
import time
import httpx
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Response
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pathlib import Path
from typing import Any, Dict, List, Optional

from src import mqtt_handler, sensor_cache
from src.config import config
from src.logger import logger
from src.database import cleanup_old_readings
from src.models import (
    BusDeparture, BusDepartures, CurrentWeather, GolemioResponse, GolemioDeparture,
    NamedayResponse, OpenMeteoResponse, FrontendConfig, SystemHealth,
    InitialStateMessage, SensorStatusMessage, TransportMessage,
    WeatherMessage, NamedayMessage, HeartbeatMessage,
    BusStop, BUS_STOP_LINES, ApiUrl, ApiParam, ApiHeader, ApiValue,
    WEATHER_CURRENT_PARAMS, WEATHER_DAILY_PARAMS, WEATHER_HOURLY_PARAMS,
    TodoistData, TodoistProject, TodoistTask, TodoistMessage,
    TodoistTaskResponse, TodoistProjectResponse,
    CalendarData, CalendarMessage,
    NhlLeague, NhlMessage, NhlPhase, NhlGameType, NhlBracket, NhlScoreGame,
    parse_nhl_score_games, parse_nhl_standings, parse_nhl_leaders, parse_nhl_bracket,
    NHL_SKATER_LEADER_CATEGORIES, NHL_GOALIE_LEADER_CATEGORIES, NHL_LEADERS_LIMIT
)
from src.system_info import live_system_stats, check_wifi_connectivity
from src.websocket_manager import manager
from src.calendar_service import GoogleCalendarService

router = APIRouter()

# Global cache for external data
latest_weather: CurrentWeather | None = None
latest_nameday: str = "..."
latest_departures: BusDepartures = BusDepartures()
latest_todoist: TodoistData | None = None
latest_calendar: CalendarData | None = None
latest_nhl: NhlLeague | None = None

# Thread safety: Lock to protect global cache variables
_cache_lock = asyncio.Lock()

# Shared HTTP client for connection pooling (Raspberry Pi optimization)
# Reuses connections instead of creating new ones for each request
_http_client: httpx.AsyncClient | None = None

# Google Calendar service instance
_calendar_service: GoogleCalendarService | None = None


def get_http_client() -> httpx.AsyncClient:
    """
    Get or create the shared HTTP client.

    This reuses connections across requests, reducing overhead on Raspberry Pi.
    """
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=10.0,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
    return _http_client


async def close_http_client():
    """Close the shared HTTP client during shutdown."""
    global _http_client
    if _http_client:
        await _http_client.aclose()
        _http_client = None
        logger.info("✅ HTTP client closed")


def get_calendar_service() -> GoogleCalendarService | None:
    """
    Get or create the Google Calendar service.

    Returns None if calendars are not configured.
    """
    global _calendar_service
    if _calendar_service is None:
        # Build calendar configs from environment
        calendar_configs = {}
        calendar_colors = {}
        if config.GOOGLE_CALENDAR_REJDY_ID:
            calendar_configs[config.GOOGLE_CALENDAR_REJDY_ID] = config.GOOGLE_CALENDAR_REJDY_NAME
            calendar_colors[config.GOOGLE_CALENDAR_REJDY_ID] = config.GOOGLE_CALENDAR_REJDY_COLOR
        if config.GOOGLE_CALENDAR_ZUZ_ID:
            calendar_configs[config.GOOGLE_CALENDAR_ZUZ_ID] = config.GOOGLE_CALENDAR_ZUZ_NAME
            calendar_colors[config.GOOGLE_CALENDAR_ZUZ_ID] = config.GOOGLE_CALENDAR_ZUZ_COLOR

        # Add bank holiday calendars
        calendar_configs[config.GOOGLE_CALENDAR_BANK_HOLIDAYS_CZ] = config.GOOGLE_CALENDAR_BANK_HOLIDAYS_CZ_NAME
        calendar_colors[config.GOOGLE_CALENDAR_BANK_HOLIDAYS_CZ] = config.GOOGLE_CALENDAR_BANK_HOLIDAYS_CZ_COLOR
        calendar_configs[config.GOOGLE_CALENDAR_BANK_HOLIDAYS_SK] = config.GOOGLE_CALENDAR_BANK_HOLIDAYS_SK_NAME
        calendar_colors[config.GOOGLE_CALENDAR_BANK_HOLIDAYS_SK] = config.GOOGLE_CALENDAR_BANK_HOLIDAYS_SK_COLOR

        if not calendar_configs:
            logger.warning("⚠️ No Google Calendar IDs configured, calendar updates disabled")
            return None

        service_account_path = Path(__file__).parent.parent / config.GOOGLE_SERVICE_ACCOUNT_FILE
        _calendar_service = GoogleCalendarService(service_account_path, calendar_configs, calendar_colors)

    return _calendar_service


async def update_calendar_data() -> None:
    """Background task to fetch Google Calendar events."""
    global latest_calendar

    calendar_service = get_calendar_service()
    if not calendar_service:
        return

    logger.info(f"📅 Calendar monitoring started")

    while True:
        try:
            # Fetch events for the current month view
            new_calendar = await calendar_service.fetch_events_async()

            async with _cache_lock:
                # Only broadcast if data changed
                if new_calendar != latest_calendar:
                    latest_calendar = new_calendar
                    logger.debug(f"📅 Calendar updated: {len(new_calendar.events)} events")
                    # Broadcast to all connected clients
                    message = CalendarMessage(calendar=latest_calendar)
                    await manager.broadcast(message.to_dict())
                else:
                    logger.debug("📅 Calendar data unchanged")

        except Exception as e:
            logger.error(f"⚠️ Calendar data error: {e}")

        await asyncio.sleep(config.GOOGLE_CALENDAR_UPDATE_INTERVAL)


def _current_nhl_season() -> str:
    """Derive the NHL season id (e.g. '20262027') from the current date, or use the override."""
    if config.NHL_SEASON:
        return config.NHL_SEASON
    now = datetime.now()
    start_year = now.year if now.month >= 9 else now.year - 1
    return f"{start_year}{start_year + 1}"


async def _fetch_nhl_json(client: httpx.AsyncClient, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """GET an NHL API endpoint; returns None (and logs) on any failure so other sections still refresh."""
    try:
        response = await client.get(url, params=params, timeout=10.0, follow_redirects=True)
        if response.status_code == 200:
            return response.json()
        logger.warning(f"⚠️ NHL API returned status {response.status_code} for {url}")
    except httpx.TimeoutException:
        logger.warning(f"⚠️ NHL API timeout for {url}")
    except Exception as e:
        logger.error(f"⚠️ NHL API error for {url}: {e}")
    return None


def _nhl_playoffs_active(bracket: NhlBracket | None, results: List[NhlScoreGame]) -> bool:
    """
    True while the playoffs are on: the bracket has matchups and the Cup is not
    decided yet — or it was decided last night (the clinching game of the
    Stanley Cup Final is among last night's results), so the champion shows on
    the morning after and then the tile returns to the regular-season views.
    """
    if bracket is None:
        return False
    if bracket.stage < 5:
        return True
    final = next((s for s in bracket.series if s.round == 4), None)
    return final is not None and any(g.series_letter == final.letter for g in results)


async def update_nhl_data() -> None:
    """
    Background task feeding the rotating NHL tile, all season long.

    Playoff mode (bracket + playoff stats) runs only while the playoffs are on:
    from the first matchups until the morning after the Cup is won (the
    clinching game is in last night's results). Before and after that the tile
    shows the regular season, so last season's bracket never lingers.

    "Last night" / "tonight" use the Prague calendar: games on NHL date D end in
    Prague's early morning of D+1, so last night's results are always the NHL
    date of yesterday (Prague). Scoreboards and the bracket refresh every cycle
    (faster while games are live); standings and leaders on slower timers.
    A failed section keeps its previous data instead of blanking the tile.
    """
    global latest_nhl

    logger.info("🏒 NHL monitoring started")

    client = get_http_client()
    prague = ZoneInfo(ApiValue.TIMEZONE_PRAGUE.value)

    season = ""
    phase = NhlPhase.REGULAR.value
    bracket = None  # this season's bracket as last fetched (None until matchups exist)
    results_date, results = "", []
    upcoming_date, upcoming = "", []
    standings: list = []
    skater_leaders: list = []
    goalie_leaders: list = []
    standings_fetched_at: float | None = None
    leaders_fetched_at: float | None = None
    leaders_key = ""  # "<season>/<game type>" the leader boards belong to

    while True:
        live = False
        try:
            current_season = _current_nhl_season()
            if current_season != season:
                # New season: forget last season's playoffs and stats
                season, phase, bracket = current_season, NhlPhase.REGULAR.value, None
                skater_leaders, goalie_leaders, leaders_key = [], [], ""
            today = datetime.now(prague).date()

            # 1) Playoff bracket
            data = await _fetch_nhl_json(client, ApiUrl.NHL_PLAYOFF_BRACKET.value.format(year=season[4:]))
            if data is not None:
                bracket = parse_nhl_bracket(data)

            # 2) Last night's scoreboard
            date = (today - timedelta(days=1)).isoformat()
            data = await _fetch_nhl_json(client, ApiUrl.NHL_SCORE.value.format(date=date))
            if data is not None:
                results_date, results = date, parse_nhl_score_games(data)

            # 3) Tonight's games (start times shown in Prague time by the frontend)
            date = today.isoformat()
            data = await _fetch_nhl_json(client, ApiUrl.NHL_SCORE.value.format(date=date))
            if data is not None:
                upcoming_date, upcoming = date, parse_nhl_score_games(data)

            # Phase: playoffs only while they are actually happening
            active_bracket = bracket if _nhl_playoffs_active(bracket, results) else None
            phase = NhlPhase.PLAYOFFS.value if active_bracket else NhlPhase.REGULAR.value

            # 4) Standings (regular season only; the bracket replaces them in the playoffs)
            now_mono = time.monotonic()
            if phase == NhlPhase.REGULAR.value and (
                    standings_fetched_at is None
                    or now_mono - standings_fetched_at >= config.NHL_STANDINGS_UPDATE_INTERVAL):
                data = await _fetch_nhl_json(client, ApiUrl.NHL_STANDINGS.value)
                if data is not None:
                    standings = parse_nhl_standings(data)
                    standings_fetched_at = now_mono

            # 5) Skater + goalie leaders for the current phase
            game_type = (NhlGameType.PLAYOFFS if phase == NhlPhase.PLAYOFFS.value else NhlGameType.REGULAR).value
            key = f"{season}/{game_type}"
            if (key != leaders_key or leaders_fetched_at is None
                    or now_mono - leaders_fetched_at >= config.NHL_LEADERS_UPDATE_INTERVAL):
                skater_data = await _fetch_nhl_json(
                    client, ApiUrl.NHL_SKATER_LEADERS.value.format(season=season, game_type=game_type), {
                        ApiParam.CATEGORIES.value: ",".join(k for k, _ in NHL_SKATER_LEADER_CATEGORIES),
                        ApiParam.LIMIT.value: NHL_LEADERS_LIMIT,
                    })
                goalie_data = await _fetch_nhl_json(
                    client, ApiUrl.NHL_GOALIE_LEADERS.value.format(season=season, game_type=game_type), {
                        ApiParam.CATEGORIES.value: ",".join(k for k, _ in NHL_GOALIE_LEADER_CATEGORIES),
                        ApiParam.LIMIT.value: NHL_LEADERS_LIMIT,
                    })
                if skater_data is not None:
                    skater_leaders = parse_nhl_leaders(skater_data, NHL_SKATER_LEADER_CATEGORIES)
                if goalie_data is not None:
                    goalie_leaders = parse_nhl_leaders(goalie_data, NHL_GOALIE_LEADER_CATEGORIES)
                if skater_data is not None and goalie_data is not None:
                    leaders_fetched_at, leaders_key = now_mono, key

            new_nhl = NhlLeague(
                season=season,
                phase=phase,
                bracket=active_bracket,
                results_date=results_date,
                results=results,
                upcoming_date=upcoming_date,
                upcoming=upcoming,
                standings=standings,
                skater_leaders=skater_leaders,
                goalie_leaders=goalie_leaders,
                updated=datetime.now().strftime("%H:%M:%S"),
            )
            live = new_nhl.has_live_games()

            async with _cache_lock:
                if latest_nhl is None or not new_nhl.equals_ignoring_updated(latest_nhl):
                    latest_nhl = new_nhl
                    logger.debug(
                        f"🏒 NHL updated: {phase}, {len(results)} results, {len(upcoming)} upcoming, "
                        f"{len(standings)} teams, stage={active_bracket.stage if active_bracket else '-'}, live={live}"
                    )
                    await manager.broadcast(NhlMessage(league=latest_nhl).to_dict())
                else:
                    latest_nhl.updated = new_nhl.updated
                    logger.debug("🏒 NHL data unchanged")

        except Exception as e:
            logger.error(f"⚠️ NHL data error: {e}", exc_info=True)

        await asyncio.sleep(config.NHL_LIVE_UPDATE_INTERVAL if live else config.NHL_UPDATE_INTERVAL)


async def update_bus_data() -> None:
    """Background task to fetch bus departure data from Golemio API."""
    global latest_departures

    if not config.GOLEMIO_API_KEY:
        logger.warning("⚠️ GOLEMIO_API_KEY not configured, bus data updates disabled")
        return

    # Build request params
    params = [(ApiParam.IDS.value, stop.value) for stop in BusStop]
    params.extend([
        (ApiParam.MODE.value, ApiValue.DEPARTURES.value),
        (ApiParam.LIMIT.value, 100)
    ])
    headers = {ApiHeader.X_ACCESS_TOKEN.value: config.GOLEMIO_API_KEY}

    logger.info("🚌 Bus data monitoring started")

    client = get_http_client()
    while True:
        try:
            response = await client.get(
                ApiUrl.GOLEMIO_DEPARTURES.value,
                params=params,
                headers=headers,
                timeout=10.0
            )
            if response.status_code == 200:
                # Parse response into typed model
                golemio_data = GolemioResponse.from_dict(response.json())

                golemio_malesicka: List[GolemioDeparture] = []
                golemio_olgy: List[GolemioDeparture] = []

                for dep in golemio_data.departures:
                    # Filter and separate by stop and line using enums
                    stop_id = dep.stop.id
                    line = dep.route.short_name

                    if stop_id == BusStop.MALESICKA.value and line in {l.value for l in
                                                                       BUS_STOP_LINES[BusStop.MALESICKA]}:
                        golemio_malesicka.append(dep)
                    elif stop_id == BusStop.OLGY_HAVLOVE.value and line in {l.value for l in
                                                                            BUS_STOP_LINES[BusStop.OLGY_HAVLOVE]}:
                        golemio_olgy.append(dep)

                # Sort by soonest first using full datetime (handles date + time correctly)
                golemio_malesicka.sort(key=lambda x: x.departure_timestamp.predicted or x.departure_timestamp.scheduled or "")
                golemio_olgy.sort(key=lambda x: x.departure_timestamp.predicted or x.departure_timestamp.scheduled or "")

                # Convert to internal model
                list_malesicka = [dep.to_bus_departure() for dep in golemio_malesicka]
                list_olgy = [dep.to_bus_departure() for dep in golemio_olgy]

                # Take top 5
                new_departures = BusDepartures(
                    malesicka=list_malesicka[:5],
                    olgy=list_olgy[:5]
                )

                async with _cache_lock:
                    if new_departures != latest_departures:
                        latest_departures = new_departures
                        logger.debug(f"🚌 Bus data updated: {len(list_malesicka)} Mal, {len(list_olgy)} Olgy")
                        # Broadcast to all connected clients
                        message = TransportMessage(transport=latest_departures)
                        await manager.broadcast(message.to_dict())
            else:
                logger.warning(f"⚠️ Golemio API returned status {response.status_code}")

        except httpx.TimeoutException:
            logger.warning("⚠️ Golemio API timeout")
        except Exception as e:
            logger.error(f"⚠️ Bus data error: {e}")

        await asyncio.sleep(config.BUS_UPDATE_INTERVAL)


async def update_nameday_data() -> None:
    """Background task to fetch Nameday once a day (or every 6 hours)."""
    global latest_nameday

    logger.info("📅 Nameday monitoring started")

    client = get_http_client()
    while True:
        try:
            logger.debug("📅 Fetching nameday...")
            response = await client.get(
                ApiUrl.NAMEDAY.value,
                params={ApiParam.COUNTRY.value: ApiValue.COUNTRY_SK.value},
                timeout=10.0
            )
            if response.status_code == 200:
                nameday_data = NamedayResponse.from_dict(response.json())

                async with _cache_lock:
                    # Only update if data changed
                    if nameday_data.nameday != latest_nameday:
                        latest_nameday = nameday_data.nameday
                        logger.info(f"✅ Nameday updated: {latest_nameday}")
                        # Broadcast to all connected clients
                        message = NamedayMessage(nameday=latest_nameday)
                        await manager.broadcast(message.to_dict())
                    else:
                        logger.debug(f"📅 Nameday unchanged: {latest_nameday}")
            else:
                logger.warning(f"⚠️ Nameday API returned status {response.status_code}")

        except httpx.TimeoutException:
            logger.warning("⚠️ Nameday API timeout")
        except Exception as e:
            logger.error(f"⚠️ Nameday API error: {e}")

        # Nameday only changes once a day, so we check every 6 hours
        await asyncio.sleep(config.NAMEDAY_UPDATE_INTERVAL)


async def update_weather_data() -> None:
    """Background task to fetch weather every 10 minutes."""
    global latest_weather

    params = {
        ApiParam.LATITUDE.value: config.LOCATION_LATITUDE,
        ApiParam.LONGITUDE.value: config.LOCATION_LONGITUDE,
        ApiParam.CURRENT.value: ",".join(WEATHER_CURRENT_PARAMS),
        ApiParam.DAILY.value: ",".join(WEATHER_DAILY_PARAMS),
        ApiParam.HOURLY.value: ",".join(WEATHER_HOURLY_PARAMS),
        # Hourly window for the temperature graph: 2h back, 22h ahead
        ApiParam.PAST_HOURS.value: 2,
        ApiParam.FORECAST_HOURS.value: 22,
        ApiParam.TIMEZONE.value: ApiValue.TIMEZONE_PRAGUE.value,
        ApiParam.FORECAST_DAYS.value: 7
    }

    logger.info("🌤️ Weather monitoring started")

    client = get_http_client()
    while True:
        try:
            response = await client.get(
                ApiUrl.OPEN_METEO.value,
                params=params,
                timeout=10.0
            )
            if response.status_code == 200:
                # Parse response into typed model
                weather_data = OpenMeteoResponse.from_dict(response.json())

                # Convert to our internal model
                new_weather = weather_data.to_current_weather()

                async with _cache_lock:
                    # Only broadcast if data changed (excluding timestamp)
                    if latest_weather is None or not new_weather.equals_ignoring_updated(latest_weather):
                        latest_weather = new_weather
                        logger.debug("🌤️ Weather updated")
                        # Broadcast to all connected clients
                        message = WeatherMessage(weather=latest_weather)
                        await manager.broadcast(message.to_dict())
                    else:
                        # Update timestamp only
                        latest_weather.updated = new_weather.updated
                        logger.debug("🌤️ Weather data unchanged, timestamp updated")
            else:
                logger.warning(f"⚠️ Weather API returned status {response.status_code}")

        except httpx.TimeoutException:
            logger.warning("⚠️ Weather API timeout")
        except Exception as e:
            logger.error(f"⚠️ Weather API error: {e}")

        await asyncio.sleep(config.WEATHER_UPDATE_INTERVAL)


async def update_todoist_data() -> None:
    """Background task to fetch Todoist tasks."""
    global latest_todoist

    if not config.TODOIST_API_KEY:
        logger.warning("⚠️ TODOIST_API_KEY not configured, Todoist updates disabled")
        return

    # Build headers using enums
    headers = {ApiHeader.AUTHORIZATION.value: f"Bearer {config.TODOIST_API_KEY}"}

    logger.info(f"📝 Todoist monitoring started (projects: {config.TODOIST_PROJECT_1}, {config.TODOIST_PROJECT_2})")

    client = get_http_client()
    while True:
        try:
            # Fetch both projects' names and tasks
            projects_to_fetch = [config.TODOIST_PROJECT_1, config.TODOIST_PROJECT_2]
            projects_data = []

            for project_id in projects_to_fetch:
                # Fetch project info
                project_response = await client.get(
                    f"{ApiUrl.TODOIST_PROJECTS.value}/{project_id}",
                    headers=headers,
                    timeout=10.0
                )

                # Fetch tasks for this project using enum for params
                tasks_response = await client.get(
                    ApiUrl.TODOIST_TASKS.value,
                    params={ApiParam.PROJECT_ID.value: project_id},
                    headers=headers,
                    timeout=10.0
                )

                if project_response.status_code == 200 and tasks_response.status_code == 200:
                    # Parse responses using proper models
                    # (unified API v1 wraps task lists in a {"results": [...]} envelope)
                    project_api = TodoistProjectResponse.from_dict(project_response.json())
                    tasks_api_list = [
                        TodoistTaskResponse.from_dict(task_data)
                        for task_data in tasks_response.json().get("results", [])
                    ]

                    # Filter only non-completed tasks and convert to internal model
                    tasks = [
                        task_api.to_todoist_task()
                        for task_api in tasks_api_list
                        if not task_api.is_completed
                    ]

                    # Sort by order
                    tasks.sort(key=lambda t: t.order)

                    # Create internal project model
                    project = TodoistProject(
                        id=project_api.id,
                        name=project_api.name,
                        tasks=tasks
                    )
                    projects_data.append(project)
                else:
                    logger.warning(f"⚠️ Todoist API error for project {project_id}: {project_response.status_code}/{tasks_response.status_code}")

            new_todoist = TodoistData(projects=projects_data)

            async with _cache_lock:
                # Only broadcast if data changed
                if new_todoist != latest_todoist:
                    latest_todoist = new_todoist
                    logger.debug(f"📝 Todoist updated: {len(projects_data)} projects")
                    # Broadcast to all connected clients
                    message = TodoistMessage(todoist=latest_todoist)
                    await manager.broadcast(message.to_dict())
                else:
                    logger.debug("📝 Todoist data unchanged")

        except httpx.TimeoutException:
            logger.warning("⚠️ Todoist API timeout")
        except Exception as e:
            logger.error(f"⚠️ Todoist API error: {e}")

        await asyncio.sleep(config.TODOIST_UPDATE_INTERVAL)


def get_system_health() -> SystemHealth:
    """Check system health status."""
    db_path = Path(__file__).parent.parent / config.DB_NAME
    return SystemHealth(
        mqtt=mqtt_handler.mqtt_connected,
        database=db_path.exists(),
        wifi=check_wifi_connectivity()
    )


async def check_sensor_status() -> None:
    """Background task to check sensor status and broadcast changes."""
    logger.info(
        f"🔍 Sensor status monitor started (timeout: {config.SENSOR_OFFLINE_TIMEOUT}s, check interval: {config.SENSOR_STATUS_CHECK_INTERVAL}s)")

    while True:
        try:
            # Check for sensors that have timed out
            changes = mqtt_handler.check_sensor_timeouts()

            if changes:
                # Broadcast updated sensor status to all clients
                sensor_status = mqtt_handler.get_sensor_status()
                message = SensorStatusMessage(sensor_status=sensor_status)
                await manager.broadcast(message.to_dict())
                logger.debug(f"📡 Broadcasted sensor status changes: {changes}")
        except Exception as e:
            logger.error(f"⚠️ Sensor status check error: {e}")

        await asyncio.sleep(config.SENSOR_STATUS_CHECK_INTERVAL)


async def cleanup_database_daily() -> None:
    """
    Background task to clean up old database readings daily.

    Critical for Raspberry Pi: Prevents SD card from filling up with historical data.
    Runs once per day at configured hour (default: 3 AM).
    """
    logger.info(f"🧹 Database cleanup scheduler started (runs daily at {config.DB_CLEANUP_HOUR}:00, keeps {config.DB_CLEANUP_DAYS} days)")

    last_cleanup_day = None

    while True:
        try:
            now = datetime.now()
            current_day = now.date()
            current_hour = now.hour

            # Run cleanup once per day at the configured hour
            if current_hour == config.DB_CLEANUP_HOUR and last_cleanup_day != current_day:
                logger.info(f"🧹 Starting scheduled database cleanup...")
                deleted_count = await asyncio.to_thread(cleanup_old_readings, config.DB_CLEANUP_DAYS)
                logger.info(f"✅ Database cleanup completed: {deleted_count} rows deleted")
                last_cleanup_day = current_day

            # Check every hour
            await asyncio.sleep(3600)

        except Exception as e:
            logger.error(f"⚠️ Database cleanup error: {e}", exc_info=True)
            await asyncio.sleep(3600)  # Wait an hour before retrying


@router.get("/")
async def get_index():
    """
    Serve the main HTML page.

    Uses FileResponse for proper async file handling and automatic caching headers.
    This is better for Raspberry Pi performance than reading file into memory.
    """
    html_path = Path(__file__).parent / "static" / "index.html"

    if not html_path.exists():
        logger.error(f"index.html not found at {html_path}")
        return HTMLResponse(f"index.html not found at {html_path}", status_code=404)

    # Use FileResponse for efficient async file serving with proper headers
    return FileResponse(html_path, media_type="text/html")


@router.get("/health")
async def health_check() -> Response:
    """
    Health check endpoint for monitoring and systemd.

    Returns:
        JSONResponse: Health status with appropriate HTTP status code
            - 200 OK if all critical systems are healthy
            - 503 Service Unavailable if any critical system is down
    """
    try:
        health = get_system_health()

        # Check if critical systems are healthy
        is_healthy = health.mqtt and health.database
        status_code = 200 if is_healthy else 503

        content = {
            "status": "healthy" if is_healthy else "unhealthy",
            "checks": {
                "mqtt": "up" if health.mqtt else "down",
                "database": "up" if health.database else "down",
                "wifi": "up" if health.wifi else "down"
            },
            "websocket_connections": len(manager.active_connections),
            "timestamp": datetime.now().isoformat()
        }

        return JSONResponse(content=content, status_code=status_code)

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            content={
                "status": "error",
                "error": "Health check failed",
                "timestamp": datetime.now().isoformat()
            },
            status_code=500
        )


@router.get("/api/config")
async def get_frontend_config():
    """Return configuration values needed by the frontend."""
    frontend_config = FrontendConfig(
        google_maps_update_interval=config.GOOGLE_MAPS_UPDATE_INTERVAL * 1000,
        google_calendar_update_interval=config.GOOGLE_CALENDAR_UPDATE_INTERVAL * 1000,
        morning_mode_start=config.MORNING_MODE_START,
        day_mode_start=config.DAY_MODE_START,
        night_mode_start=config.NIGHT_MODE_START,
        nhl_tile_rotate_interval=config.NHL_TILE_ROTATE_INTERVAL * 1000
    )
    logger.info(f"📋 Config API: {frontend_config.to_dict()}")
    return frontend_config.to_dict()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates."""
    await manager.connect(websocket)

    try:
        # Send initial full state on connect
        # Use cached sensor data instead of DB query for better performance
        cached_sensors = sensor_cache.get_all()

        async with _cache_lock:
            initial_state = InitialStateMessage(
                sensors=cached_sensors,
                sensor_status=mqtt_handler.get_sensor_status(),
                system=live_system_stats,
                weather=latest_weather,
                nameday=latest_nameday,
                health=get_system_health(),
                transport=latest_departures,
                todoist=latest_todoist,
                calendar=latest_calendar,
                nhl=latest_nhl
            )

        await websocket.send_json(initial_state.to_dict())

        # Keep connection alive, waiting for messages or disconnect
        while True:
            # Wait for any message from client (ping/pong or commands)
            # This keeps the connection open without busy-polling
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send a heartbeat to keep connection alive
                await websocket.send_json(HeartbeatMessage().to_dict())

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"⚠️ WebSocket error: {e}")
        manager.disconnect(websocket)
