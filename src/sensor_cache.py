"""
In-memory sensor cache to reduce database queries.

This module maintains a cache of current sensor readings in memory,
avoiding repeated database queries on every MQTT message.
Critical for Raspberry Pi performance to reduce SD card I/O.
"""
from datetime import datetime
from typing import Dict, Tuple, List

from src.models import SensorReading
from src.logger import logger

# Key: (sensor_name, property), Value: SensorReading
_cache: Dict[Tuple[str, str], SensorReading] = {}


def update(name: str, prop: str, val: float) -> None:
    """Update the cache with a new sensor reading."""
    key = (name, prop)
    _cache[key] = SensorReading(
        sensor=name,
        prop=prop,
        temp=val,
        ts=datetime.now().isoformat()
    )


def get_all() -> List[SensorReading]:
    """Get all cached sensor readings as a list."""
    return list(_cache.values())


def get_all_as_dicts() -> List[dict]:
    """Get all cached sensor readings as dictionaries."""
    return [sensor.to_dict() for sensor in _cache.values()]


def load_from_db() -> None:
    """Load sensor readings from database into cache (called on startup)."""
    from src.database import get_current_status

    db_sensors = get_current_status()
    for sensor in db_sensors:
        _cache[(sensor.sensor, sensor.prop)] = sensor

    logger.info(f"✅ Loaded {len(_cache)} sensor readings into cache")


def is_empty() -> bool:
    """Check if cache is empty."""
    return len(_cache) == 0


def clear() -> None:
    """Clear the cache (for testing/debugging)."""
    _cache.clear()
