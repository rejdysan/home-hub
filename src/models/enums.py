"""Enums and constants used across the application."""
from enum import Enum
from typing import Dict, List, Set


class ThermalSensor(str, Enum):
    """Known thermal sensor names across different platforms."""
    CPU_THERMAL = "cpu_thermal"  # Raspberry Pi
    CORETEMP = "coretemp"  # Intel CPUs
    K10TEMP = "k10temp"  # AMD CPUs
    ACPITZ = "acpitz"  # ACPI thermal zone


# Priority order for temperature sensor lookup
THERMAL_SENSOR_PRIORITY: List[ThermalSensor] = [
    ThermalSensor.CPU_THERMAL,
    ThermalSensor.CORETEMP,
    ThermalSensor.K10TEMP,
    ThermalSensor.ACPITZ,
]


class WebSocketMessageType(str, Enum):
    """WebSocket message type identifiers."""
    INITIAL = "initial"
    SENSOR_STATUS = "sensor_status"
    TRANSPORT = "transport"
    WEATHER = "weather"
    NAMEDAY = "nameday"
    SYSTEM = "system"
    HEARTBEAT = "heartbeat"
    TODOIST = "todoist"
    CALENDAR = "calendar"


class BusStop(str, Enum):
    """Prague bus stop IDs."""
    MALESICKA = "U357Z1P"
    OLGY_HAVLOVE = "U1064Z2P"


class BusLine(str, Enum):
    """Prague bus line numbers."""
    LINE_133 = "133"
    LINE_146 = "146"
    LINE_155 = "155"


# Which lines to track at each stop
BUS_STOP_LINES: Dict[BusStop, Set[BusLine]] = {
    BusStop.MALESICKA: {BusLine.LINE_146, BusLine.LINE_155},
    BusStop.OLGY_HAVLOVE: {BusLine.LINE_133},
}


class ApiUrl(str, Enum):
    """External API URLs."""
    GOLEMIO_DEPARTURES = "https://api.golemio.cz/v2/pid/departureboards"
    NAMEDAY = "https://nameday.abalin.net/api/V2/today"
    OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
    TODOIST_TASKS = "https://api.todoist.com/rest/v2/tasks"
    TODOIST_PROJECTS = "https://api.todoist.com/rest/v2/projects"



# OpenMeteo API parameters
WEATHER_CURRENT_PARAMS: List[str] = [
    "temperature_2m",
    "apparent_temperature",
    "is_day",
    "weather_code",
    "wind_speed_10m",
    "relative_humidity_2m",
    "pressure_msl",
    "uv_index",
    "cloud_cover",
    "visibility",
]

WEATHER_DAILY_PARAMS: List[str] = [
    "temperature_2m_max",
    "temperature_2m_min",
    "weather_code",
]


class ApiParam(str, Enum):
    """API query parameter names."""
    # OpenMeteo
    LATITUDE = "latitude"
    LONGITUDE = "longitude"
    CURRENT = "current"
    DAILY = "daily"
    TIMEZONE = "timezone"
    FORECAST_DAYS = "forecast_days"
    # Golemio
    IDS = "ids"
    MODE = "mode"
    LIMIT = "limit"
    # Nameday
    COUNTRY = "country"
    # Todoist
    PROJECT_ID = "project_id"
    # Google Calendar
    CALENDAR_ID = "calendarId"
    TIME_MIN = "timeMin"
    TIME_MAX = "timeMax"
    MAX_RESULTS = "maxResults"
    SINGLE_EVENTS = "singleEvents"
    ORDER_BY = "orderBy"
    TIME_ZONE = "timeZone"


class ApiHeader(str, Enum):
    """API header names."""
    X_ACCESS_TOKEN = "X-Access-Token"
    AUTHORIZATION = "Authorization"


class ApiValue(str, Enum):
    """Common API parameter values."""
    # Golemio modes
    DEPARTURES = "departures"
    # Timezones
    TIMEZONE_PRAGUE = "Europe/Prague"
    # Countries
    COUNTRY_SK = "sk"
    # Google Calendar
    ORDER_BY_START_TIME = "startTime"


class ApiResponseKey(str, Enum):
    """Common API response keys."""
    ITEMS = "items"


class WeatherCode(int, Enum):
    """WMO Weather interpretation codes (WW) from Open-Meteo API."""
    CLEAR_SKY = 0
    MAINLY_CLEAR = 1
    PARTLY_CLOUDY = 2
    OVERCAST = 3
    FOG = 45
    DEPOSITING_RIME_FOG = 48
    LIGHT_DRIZZLE = 51
    MODERATE_DRIZZLE = 53
    DENSE_DRIZZLE = 55
    LIGHT_FREEZING_DRIZZLE = 56
    DENSE_FREEZING_DRIZZLE = 57
    SLIGHT_RAIN = 61
    MODERATE_RAIN = 63
    HEAVY_RAIN = 65
    LIGHT_FREEZING_RAIN = 66
    HEAVY_FREEZING_RAIN = 67
    SLIGHT_SNOW = 71
    MODERATE_SNOW = 73
    HEAVY_SNOW = 75
    SNOW_GRAINS = 77
    SLIGHT_RAIN_SHOWERS = 80
    MODERATE_RAIN_SHOWERS = 81
    VIOLENT_RAIN_SHOWERS = 82
    SLIGHT_SNOW_SHOWERS = 85
    HEAVY_SNOW_SHOWERS = 86
    THUNDERSTORM = 95
    THUNDERSTORM_SLIGHT_HAIL = 96
    THUNDERSTORM_HEAVY_HAIL = 99

    @property
    def description(self) -> str:
        """Human-readable description of the weather code."""
        return WEATHER_DESCRIPTIONS.get(self.value, "Unknown")


# Weather code to description mapping
WEATHER_DESCRIPTIONS: Dict[int, str] = {
    WeatherCode.CLEAR_SKY: "Clear sky",
    WeatherCode.MAINLY_CLEAR: "Mainly clear",
    WeatherCode.PARTLY_CLOUDY: "Partly cloudy",
    WeatherCode.OVERCAST: "Overcast",
    WeatherCode.FOG: "Fog",
    WeatherCode.DEPOSITING_RIME_FOG: "Depositing rime fog",
    WeatherCode.LIGHT_DRIZZLE: "Light drizzle",
    WeatherCode.MODERATE_DRIZZLE: "Moderate drizzle",
    WeatherCode.DENSE_DRIZZLE: "Dense drizzle",
    WeatherCode.LIGHT_FREEZING_DRIZZLE: "Light freezing drizzle",
    WeatherCode.DENSE_FREEZING_DRIZZLE: "Dense freezing drizzle",
    WeatherCode.SLIGHT_RAIN: "Slight rain",
    WeatherCode.MODERATE_RAIN: "Moderate rain",
    WeatherCode.HEAVY_RAIN: "Heavy rain",
    WeatherCode.LIGHT_FREEZING_RAIN: "Light freezing rain",
    WeatherCode.HEAVY_FREEZING_RAIN: "Heavy freezing rain",
    WeatherCode.SLIGHT_SNOW: "Slight snow fall",
    WeatherCode.MODERATE_SNOW: "Moderate snow fall",
    WeatherCode.HEAVY_SNOW: "Heavy snow fall",
    WeatherCode.SNOW_GRAINS: "Snow grains",
    WeatherCode.SLIGHT_RAIN_SHOWERS: "Slight rain showers",
    WeatherCode.MODERATE_RAIN_SHOWERS: "Moderate rain showers",
    WeatherCode.VIOLENT_RAIN_SHOWERS: "Violent rain showers",
    WeatherCode.SLIGHT_SNOW_SHOWERS: "Slight snow showers",
    WeatherCode.HEAVY_SNOW_SHOWERS: "Heavy snow showers",
    WeatherCode.THUNDERSTORM: "Thunderstorm",
    WeatherCode.THUNDERSTORM_SLIGHT_HAIL: "Thunderstorm with slight hail",
    WeatherCode.THUNDERSTORM_HEAVY_HAIL: "Thunderstorm with heavy hail",
}
