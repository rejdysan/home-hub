"""Configuration management for Home Hub application."""
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file in project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Config:
    """Application configuration."""

    # MQTT Configuration
    MQTT_BROKER: str = os.getenv("MQTT_BROKER", "localhost")
    MQTT_PORT: int = int(os.getenv("MQTT_PORT", "1883"))
    MQTT_USER: Optional[str] = os.getenv("MQTT_USER")
    MQTT_PASS: Optional[str] = os.getenv("MQTT_PASS")
    MQTT_KEEPALIVE: int = int(os.getenv("MQTT_KEEPALIVE", "60"))

    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # API Keys
    GOLEMIO_API_KEY: Optional[str] = os.getenv("GOLEMIO_API_KEY")
    TODOIST_API_KEY: Optional[str] = os.getenv("TODOIST_API_KEY")

    # Todoist Project IDs
    TODOIST_PROJECT_1: str = os.getenv("TODOIST_PROJECT_1", "2364746733")
    TODOIST_PROJECT_2: str = os.getenv("TODOIST_PROJECT_2", "2364815186")

    # Location
    LOCATION_LATITUDE: str = os.getenv("LOCATION_LATITUDE", "50.0878433")
    LOCATION_LONGITUDE: str = os.getenv("LOCATION_LONGITUDE", "14.478581")

    # Update Intervals (in seconds)
    WEATHER_UPDATE_INTERVAL: int = int(os.getenv("WEATHER_UPDATE_INTERVAL", "600"))  # 10 minutes
    NAMEDAY_UPDATE_INTERVAL: int = int(os.getenv("NAMEDAY_UPDATE_INTERVAL", "21600"))  # 6 hours
    BUS_UPDATE_INTERVAL: int = int(os.getenv("BUS_UPDATE_INTERVAL", "30"))  # 30 seconds
    # Reduced default from 2 to 5 seconds for better Raspberry Pi performance
    SYSTEM_MONITOR_INTERVAL: int = int(os.getenv("SYSTEM_MONITOR_INTERVAL", "5"))  # 5 seconds
    WEBSOCKET_UPDATE_INTERVAL: int = int(os.getenv("WEBSOCKET_UPDATE_INTERVAL", "1"))  # 1 second
    GOOGLE_MAPS_UPDATE_INTERVAL: int = int(os.getenv("GOOGLE_MAPS_UPDATE_INTERVAL", "60"))  # 60 seconds
    TODOIST_UPDATE_INTERVAL: int = int(os.getenv("TODOIST_UPDATE_INTERVAL", "60"))  # 60 seconds
    GOOGLE_CALENDAR_UPDATE_INTERVAL: int = int(os.getenv("GOOGLE_CALENDAR_UPDATE_INTERVAL", "300"))  # 5 minutes

    # MQTT Throttle
    MQTT_SAVE_THROTTLE: int = int(os.getenv("MQTT_SAVE_THROTTLE", "5"))  # 5 seconds

    # Sensor Status Tracking
    SENSOR_OFFLINE_TIMEOUT: int = int(os.getenv("SENSOR_OFFLINE_TIMEOUT", "30"))  # 30 seconds (sensors send every 10s)
    SENSOR_STATUS_CHECK_INTERVAL: int = int(os.getenv("SENSOR_STATUS_CHECK_INTERVAL", "5"))  # Check every 5 seconds

    # Database
    DB_NAME: str = os.getenv("DB_NAME", "sensors.db")
    DB_CLEANUP_DAYS: int = int(os.getenv("DB_CLEANUP_DAYS", "30"))  # Keep 30 days of readings
    DB_CLEANUP_HOUR: int = int(os.getenv("DB_CLEANUP_HOUR", "3"))  # Run cleanup at 3 AM

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Kiosk Modes (time in HH:MM format)
    MORNING_MODE_START: str = os.getenv("MORNING_MODE_START", "05:30")
    DAY_MODE_START: str = os.getenv("DAY_MODE_START", "08:00")
    NIGHT_MODE_START: str = os.getenv("NIGHT_MODE_START", "22:00")


config = Config()

