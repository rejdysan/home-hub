"""
Models package for home-hub application.

This package contains all data models organized by category:
- enums: Enumerations and constants
- external_apis: Models for parsing external API responses (Golemio, OpenMeteo, Nameday)
- internal: Internal application models (sensors, weather, transport)
- websocket: WebSocket message models
"""

# Enums and constants
from .enums import (
    ThermalSensor,
    THERMAL_SENSOR_PRIORITY,
    WeatherCode,
    WEATHER_DESCRIPTIONS,
    WebSocketMessageType,
    BusStop,
    BusLine,
    BUS_STOP_LINES,
    ApiUrl,
    ApiParam,
    ApiHeader,
    ApiValue,
    ApiResponseKey,
    WEATHER_CURRENT_PARAMS,
    WEATHER_DAILY_PARAMS,
)

# External API models
from .external_apis import (
    GolemioTimestamp,
    GolemioDelay,
    GolemioRoute,
    GolemioStop,
    GolemioTrip,
    GolemioDeparture,
    GolemioResponse,
    NamedayResponse,
    OpenMeteoCurrent,
    OpenMeteoDaily,
    OpenMeteoResponse,
    TodoistTaskResponse,
    TodoistProjectResponse,
    GoogleCalendarEventTime,
    GoogleCalendarEventResponse,
)

# Internal application models
from .internal import (
    FrontendConfig,
    SystemStats,
    SensorStatus,
    SensorReading,
    SystemHealth,
    BusDeparture,
    BusDepartures,
    CurrentWeather,
    TodoistTask,
    TodoistProject,
    TodoistData,
    CalendarEvent,
    CalendarData,
)

# WebSocket message models
from .websocket import (
    BaseWebSocketMessage,
    SensorStatusMessage,
    TransportMessage,
    WeatherMessage,
    NamedayMessage,
    SystemMessage,
    HeartbeatMessage,
    InitialStateMessage,
    TodoistMessage,
    CalendarMessage,
)

__all__ = [
    # Enums
    "ThermalSensor",
    "THERMAL_SENSOR_PRIORITY",
    "WeatherCode",
    "WEATHER_DESCRIPTIONS",
    "WebSocketMessageType",
    "BusStop",
    "BusLine",
    "BUS_STOP_LINES",
    "ApiUrl",
    "ApiParam",
    "ApiHeader",
    "ApiValue",
    "ApiResponseKey",
    "WEATHER_CURRENT_PARAMS",
    "WEATHER_DAILY_PARAMS",
    # External APIs
    "GolemioTimestamp",
    "GolemioDelay",
    "GolemioRoute",
    "GolemioStop",
    "GolemioTrip",
    "GolemioDeparture",
    "GolemioResponse",
    "NamedayResponse",
    "OpenMeteoCurrent",
    "OpenMeteoDaily",
    "OpenMeteoResponse",
    "TodoistTaskResponse",
    "TodoistProjectResponse",
    "GoogleCalendarEventTime",
    "GoogleCalendarEventResponse",
    # Internal
    "FrontendConfig",
    "SystemStats",
    "SensorStatus",
    "SensorReading",
    "SystemHealth",
    "BusDeparture",
    "BusDepartures",
    "CurrentWeather",
    "TodoistTask",
    "TodoistProject",
    "TodoistData",
    "CalendarEvent",
    "CalendarData",
    # WebSocket
    "BaseWebSocketMessage",
    "TodoistMessage",
    "CalendarMessage",
    "SensorStatusMessage",
    "TransportMessage",
    "WeatherMessage",
    "NamedayMessage",
    "SystemMessage",
    "HeartbeatMessage",
    "InitialStateMessage",
]

