import time
import datetime
import re
import threading
import paho.mqtt.client as mqtt
from typing import Dict, Tuple, Optional, Callable, Any
from paho.mqtt.client import Client, MQTTMessage

from src.config import config
from src.logger import logger
from src.database import save_reading
from src.models import SensorStatus

# Validation constants for MQTT message security
MAX_SENSOR_NAME_LENGTH = 50
MAX_PROPERTY_NAME_LENGTH = 50
VALID_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-]+$')  # Alphanumeric, underscore, hyphen only
VALID_PROPERTIES = {'temperature', 'humidity', 'pressure'}  # Allowed property types
MIN_TEMP_VALUE = -50.0  # Minimum realistic temperature (Celsius)
MAX_TEMP_VALUE = 100.0  # Maximum realistic temperature (Celsius)
MIN_HUMIDITY_VALUE = 0.0
MAX_HUMIDITY_VALUE = 100.0
MIN_PRESSURE_VALUE = 800.0  # hPa
MAX_PRESSURE_VALUE = 1200.0  # hPa

mqtt_connected = False
last_save_time: Dict[Tuple[str, str], float] = {}

# Sensor status tracking - stores last seen timestamp per sensor
sensor_last_seen: Dict[str, float] = {}
sensor_online_status: Dict[str, bool] = {}

# Thread safety: Lock to protect shared state accessed by MQTT thread and async tasks
_state_lock = threading.Lock()

# Callback to broadcast sensor updates (set from main.py)
_sensor_callback: Optional[Callable] = None
# Callback to notify when sensor status changes (online/offline)
_status_change_callback: Optional[Callable] = None


def set_sensor_callback(callback: Callable):
    """Set callback to notify when sensor data arrives."""
    global _sensor_callback
    _sensor_callback = callback


def set_status_change_callback(callback: Callable):
    """Set callback to notify when sensor online/offline status changes."""
    global _status_change_callback
    _status_change_callback = callback


def get_sensor_status() -> Dict[str, SensorStatus]:
    """Get current online/offline status for all sensors."""
    current_time = time.time()
    status = {}
    with _state_lock:
        for sensor, last_seen in sensor_last_seen.items():
            is_online = (current_time - last_seen) < config.SENSOR_OFFLINE_TIMEOUT
            status[sensor] = SensorStatus(
                online=is_online,
                last_seen=last_seen,
                seconds_ago=round(current_time - last_seen, 1)
            )
    return status


def validate_mqtt_message(name: str, prop: str, val: float) -> Tuple[bool, Optional[str]]:
    """
    Validate MQTT message data to prevent injection and ensure data integrity.

    Args:
        name: Sensor name
        prop: Property name (temperature, humidity, pressure)
        val: Sensor value

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate sensor name length
    if len(name) > MAX_SENSOR_NAME_LENGTH:
        return False, f"Sensor name too long: {len(name)} > {MAX_SENSOR_NAME_LENGTH}"

    # Validate sensor name format (prevent SQL injection)
    if not VALID_NAME_PATTERN.match(name):
        return False, f"Invalid sensor name format: {name}"

    # Validate property name length
    if len(prop) > MAX_PROPERTY_NAME_LENGTH:
        return False, f"Property name too long: {len(prop)} > {MAX_PROPERTY_NAME_LENGTH}"

    # Validate property name format
    if not VALID_NAME_PATTERN.match(prop):
        return False, f"Invalid property name format: {prop}"

    # Validate property is allowed
    if prop not in VALID_PROPERTIES:
        return False, f"Unknown property type: {prop}. Allowed: {VALID_PROPERTIES}"

    # Validate value ranges based on property type
    if prop == 'temperature':
        if not (MIN_TEMP_VALUE <= val <= MAX_TEMP_VALUE):
            return False, f"Temperature out of range: {val} (expected {MIN_TEMP_VALUE} to {MAX_TEMP_VALUE})"
    elif prop == 'humidity':
        if not (MIN_HUMIDITY_VALUE <= val <= MAX_HUMIDITY_VALUE):
            return False, f"Humidity out of range: {val} (expected {MIN_HUMIDITY_VALUE} to {MAX_HUMIDITY_VALUE})"
    elif prop == 'pressure':
        if not (MIN_PRESSURE_VALUE <= val <= MAX_PRESSURE_VALUE):
            return False, f"Pressure out of range: {val} (expected {MIN_PRESSURE_VALUE} to {MAX_PRESSURE_VALUE})"

    return True, None


def check_sensor_timeouts() -> Dict[str, bool]:
    """
    Check if any sensors have timed out and update their status.
    Returns dict of sensors that changed status.
    """
    global sensor_online_status
    current_time = time.time()
    changes = {}

    with _state_lock:
        for sensor, last_seen in list(sensor_last_seen.items()):
            was_online = sensor_online_status.get(sensor, True)
            is_online = (current_time - last_seen) < config.SENSOR_OFFLINE_TIMEOUT

            if was_online != is_online:
                sensor_online_status[sensor] = is_online
                changes[sensor] = is_online
                if is_online:
                    logger.info(f"🟢 Sensor '{sensor}' is back online")
                else:
                    logger.warning(f"🔴 Sensor '{sensor}' went offline (last seen {round(current_time - last_seen)}s ago)")

    return changes


def on_connect(client: Client, userdata: None, flags: Dict[str, Any], reason_code: int, properties: Optional[Any] = None) -> None:
    """
    Handle MQTT connection events.

    Args:
        client: MQTT client instance
        userdata: User data (not used in this application)
        flags: Connection flags dictionary
        reason_code: Connection result code (0 = success)
        properties: MQTT v5 properties (optional, not used)
    """
    global mqtt_connected
    if reason_code == 0:
        mqtt_connected = True
        logger.info("✅ MQTT Connected")
        client.subscribe("pico/+/+")
        logger.info("📡 Subscribed to pico/+/+")
    else:
        mqtt_connected = False
        logger.error(f"❌ MQTT Connection Failed: {reason_code}")


def on_disconnect(client: Client, userdata: None, flags: Dict[str, Any], reason_code: int, properties: Optional[Any] = None) -> None:
    """
    Handle MQTT disconnection events.

    Args:
        client: MQTT client instance
        userdata: User data (not used in this application)
        flags: Disconnection flags dictionary
        reason_code: Disconnection result code (0 = clean disconnect)
        properties: MQTT v5 properties (optional, not used)
    """
    global mqtt_connected
    mqtt_connected = False
    if reason_code == 0:
        logger.info("⚠️ Disconnected from MQTT Broker (expected)")
    else:
        logger.warning(f"⚠️ Unexpected disconnect from MQTT Broker: {reason_code}")


def on_message(client: Client, userdata: None, msg: MQTTMessage) -> None:
    """
    Handle incoming MQTT messages.

    Parses topic in format 'pico/{property}/{sensor_name}' and validates/stores the reading.

    Args:
        client: MQTT client instance
        userdata: User data (not used in this application)
        msg: MQTT message containing topic and payload
    """
    global sensor_online_status
    try:
        parts = msg.topic.split('/')
        if len(parts) < 3:
            logger.warning(f"⚠️ Invalid topic format: {msg.topic}")
            return

        prop, name = parts[-2], parts[-1]

        try:
            val = float(msg.payload.decode())
        except ValueError as e:
            logger.warning(f"⚠️ Invalid payload value: {msg.payload} - {e}")
            return

        # Validate message data before processing
        is_valid, error_msg = validate_mqtt_message(name, prop, val)
        if not is_valid:
            logger.warning(f"⚠️ MQTT validation failed: {error_msg}")
            return

        current_time = time.time()
        should_save = False
        status_changed = False

        # Protect shared state with lock
        with _state_lock:
            # Update last seen time for this sensor
            sensor_last_seen[name] = current_time

            # Check if sensor just came back online
            was_online = sensor_online_status.get(name, False)
            if not was_online:
                sensor_online_status[name] = True
                status_changed = True
                logger.info(f"🟢 Sensor '{name}' is now online")

            # Throttle saving to DB (configurable window)
            key = (name, prop)
            if (current_time - last_save_time.get(key, 0)) >= config.MQTT_SAVE_THROTTLE:
                last_save_time[key] = current_time
                should_save = True

        # Perform I/O operations outside the lock
        if status_changed and _status_change_callback:
            _status_change_callback(name, True)

        if should_save:
            save_reading(name, prop, val)
            logger.debug(f"💾 Saved: {name} [{prop}] -> {val} at {datetime.datetime.now()}")

        # Notify about new sensor data
        if _sensor_callback:
            _sensor_callback(name, prop, val)

    except Exception as e:
        logger.error(f"⚠️ MQTT Message Error: {e}", exc_info=True)


def setup_mqtt() -> mqtt.Client:
    """Initialize and configure MQTT client."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    # Set credentials if provided
    if config.MQTT_USER and config.MQTT_PASS:
        client.username_pw_set(config.MQTT_USER, config.MQTT_PASS)
        logger.info(f"🔐 MQTT authentication configured for user: {config.MQTT_USER}")

    # Assign callbacks
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    # Configure reconnection logic
    client.reconnect_delay_set(min_delay=1, max_delay=120)

    return client


