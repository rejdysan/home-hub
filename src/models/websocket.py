"""WebSocket message models."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List

from .enums import WebSocketMessageType
from .internal import (
    SensorStatus, SensorReading, SystemStats, SystemHealth,
    BusDepartures, CurrentWeather, TodoistData
)


class BaseWebSocketMessage(ABC):
    """Abstract base class for all WebSocket messages."""

    @property
    @abstractmethod
    def message_type(self) -> WebSocketMessageType:
        """Message type identifier."""
        pass

    @property
    @abstractmethod
    def data(self) -> Any:
        """Message payload."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for JSON serialization."""
        result = {"type": self.message_type.value}
        payload = self.data
        if payload is not None:
            result["data"] = payload
        return result


@dataclass
class SensorStatusMessage(BaseWebSocketMessage):
    """WebSocket message for sensor status updates."""
    sensor_status: Dict[str, SensorStatus]

    @property
    def message_type(self) -> WebSocketMessageType:
        return WebSocketMessageType.SENSOR_STATUS

    @property
    def data(self) -> Dict[str, Any]:
        return {k: asdict(v) for k, v in self.sensor_status.items()}


@dataclass
class TransportMessage(BaseWebSocketMessage):
    """WebSocket message for transport/bus updates."""
    transport: BusDepartures

    @property
    def message_type(self) -> WebSocketMessageType:
        return WebSocketMessageType.TRANSPORT

    @property
    def data(self) -> Dict[str, Any]:
        return {
            "malesicka": [asdict(dep) for dep in self.transport.malesicka],
            "olgy": [asdict(dep) for dep in self.transport.olgy]
        }


@dataclass
class WeatherMessage(BaseWebSocketMessage):
    """WebSocket message for weather updates."""
    weather: CurrentWeather

    @property
    def message_type(self) -> WebSocketMessageType:
        return WebSocketMessageType.WEATHER

    @property
    def data(self) -> Dict[str, Any]:
        return asdict(self.weather)


@dataclass
class NamedayMessage(BaseWebSocketMessage):
    """WebSocket message for nameday updates."""
    nameday: str

    @property
    def message_type(self) -> WebSocketMessageType:
        return WebSocketMessageType.NAMEDAY

    @property
    def data(self) -> str:
        return self.nameday


@dataclass
class SystemMessage(BaseWebSocketMessage):
    """WebSocket message for system stats updates."""
    system: SystemStats

    @property
    def message_type(self) -> WebSocketMessageType:
        return WebSocketMessageType.SYSTEM

    @property
    def data(self) -> Dict[str, Any]:
        return asdict(self.system)


@dataclass
class HeartbeatMessage(BaseWebSocketMessage):
    """WebSocket heartbeat message."""

    @property
    def message_type(self) -> WebSocketMessageType:
        return WebSocketMessageType.HEARTBEAT

    @property
    def data(self) -> None:
        return None


@dataclass
class TodoistMessage(BaseWebSocketMessage):
    """WebSocket message for Todoist updates."""
    todoist: TodoistData

    @property
    def message_type(self) -> WebSocketMessageType:
        return WebSocketMessageType.TODOIST

    @property
    def data(self) -> Dict[str, Any]:
        return self.todoist.to_dict()


@dataclass
class InitialStateMessage(BaseWebSocketMessage):
    """Initial state sent to WebSocket clients on connect."""
    sensors: List[SensorReading]
    sensor_status: Dict[str, SensorStatus]
    system: SystemStats
    weather: Optional[CurrentWeather]
    nameday: str
    health: SystemHealth
    transport: BusDepartures
    todoist: Optional[TodoistData]

    @property
    def message_type(self) -> WebSocketMessageType:
        return WebSocketMessageType.INITIAL

    @property
    def data(self) -> None:
        # Initial message embeds data directly, not in a "data" field
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Override to flatten structure for initial state."""
        return {
            "type": self.message_type.value,
            "sensors": [asdict(s) for s in self.sensors],
            "sensor_status": {k: asdict(v) for k, v in self.sensor_status.items()},
            "system": asdict(self.system),
            "weather": asdict(self.weather) if self.weather else None,
            "nameday": self.nameday,
            "health": asdict(self.health),
            "transport": {
                "malesicka": [asdict(dep) for dep in self.transport.malesicka],
                "olgy": [asdict(dep) for dep in self.transport.olgy]
            },
            "todoist": self.todoist.to_dict() if self.todoist else None
        }
