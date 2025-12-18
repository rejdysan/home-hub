# Example for 'balcony' multisensor (temperature, humidity, pressure)
```python
"""
Raspberry Pi Pico W - BME280 Multi-Sensor to MQTT
==================================================
Reads temperature, humidity, and pressure from a BME280 sensor via I2C 
and publishes the data to an MQTT broker. Features automatic reconnection, 
watchdog timer for stability, and LED status indicators.
"""

import machine
import time
import network
import gc
from umqtt.simple import MQTTClient
import config  # Contains wifi_ssid, wifi_password, mqtt_server, mqtt_username, mqtt_password
import onewire
import BME280

# ============================================================================
# NETWORK CONFIGURATION
# ============================================================================
# Static IP configuration for stable network address
STATIC_IP = '192.168.0.53'
SUBNET_MASK = '255.255.255.0'
GATEWAY_IP = '192.168.0.1'
DNS_SERVER = '8.8.8.8'

# ============================================================================
# MQTT CONFIGURATION
# ============================================================================
MQTT_TOPIC_TEMPERATURE = 'pico/temperature/balcony'  # Topic for temperature data
MQTT_TOPIC_HUMIDITY = 'pico/humidity/balcony'        # Topic for humidity data
MQTT_TOPIC_PRESSURE = 'pico/pressure/balcony'        # Topic for pressure data
MQTT_SERVER = config.mqtt_server  # MQTT broker address (from config.py)
MQTT_PORT = 1883  # Standard MQTT port (non-SSL)
MQTT_USER = config.mqtt_username  # MQTT authentication username
MQTT_PASSWORD = config.mqtt_password  # MQTT authentication password
MQTT_CLIENT_ID = b"raspberrypi_pico_balcony"  # Unique identifier for this MQTT client
MQTT_KEEPALIVE = 60  # Seconds between keepalive pings
MQTT_SSL = False  # Disable SSL for local Mosquitto broker
MQTT_SSL_PARAMS = {'server_hostname': MQTT_SERVER}  # SSL parameters (unused when SSL=False)

# ============================================================================
# HARDWARE SETUP
# ============================================================================
# BME280 sensor via I2C: SCL on GPIO 5, SDA on GPIO 4
# Using lower frequency (10kHz) for reliable communication with BME280
i2c = machine.I2C(id=0, scl=machine.Pin(5), sda=machine.Pin(4), freq=10000)

# Onboard LED for status indication
led = machine.Pin("LED", machine.Pin.OUT)

# Watchdog Timer: Auto-resets Pico if wdt.feed() not called within 8 seconds
# Prevents device from hanging indefinitely
wdt = machine.WDT(timeout=8000)

# ============================================================================
# LED STATUS PATTERNS
# ============================================================================
# Visual feedback system for monitoring device state without serial connection:
#  - Slow blink (0.5s):     WiFi connecting
#  - 2 quick blinks:        Connection success
#  - 3 medium blinks:       WiFi error
#  - 4 fast blinks:         MQTT error
#  - 2 very fast blinks:    Sensor error (non-critical)
#  - 5 fast blinks:         General/unexpected error
#  - Brief off-pulse (50ms): Heartbeat - data successfully sent

def signal_wifi_connecting():
    """Single slow blink during WiFi connection attempts."""
    led.on()
    time.sleep(0.5)
    led.off()
    time.sleep(0.5)

def signal_success():
    """Two quick blinks for successful connection, then stays ON."""
    for _ in range(2):
        led.on()
        time.sleep(0.1)
        led.off()
        time.sleep(0.1)
    led.on()  # LED remains ON to indicate connected state

def signal_error(error_type='general'):
    """Blink patterns to identify different error types."""
    if error_type == 'wifi':
        blinks = 3
        delay = 0.2
    elif error_type == 'mqtt':
        blinks = 4
        delay = 0.15
    elif error_type == 'sensor':
        blinks = 2  # Less critical, fewer blinks
        delay = 0.1
    else:
        blinks = 5  # General/unexpected errors
        delay = 0.15
    
    for _ in range(blinks):
        led.on()
        time.sleep(delay)
        led.off()
        time.sleep(delay)

def signal_heartbeat():
    """Brief off-pulse to confirm data transmission without serial monitor."""
    led.off()
    time.sleep_ms(50)
    led.on()

# ============================================================================
# DATA STRUCTURES
# ============================================================================

class SensorData:
    """
    Container for BME280 sensor readings.
    
    Attributes:
        temp (str): Temperature reading with unit (e.g., "23.5C")
        hum (str): Humidity reading with unit (e.g., "45.2%")
        pres (str): Pressure reading with unit (e.g., "101.3hPa")
    """
    def __init__(self, temp, hum, pres):
        self.temp = temp
        self.hum = hum
        self.pres = pres
    
    def __str__(self):
        """Format sensor data for MQTT publishing."""
        return f"temp:{self.temp},hum:{self.hum},pres:{self.pres}"

# ============================================================================
# SENSOR FUNCTIONS
# ============================================================================

def get_sensor_readings():
    """
    Reads temperature, humidity, and pressure from BME280 sensor.
    
    Returns:
        SensorData: Object containing all sensor readings, or None if reading failed
        
    Note: BME280 communicates via I2C and provides temperature (°C), 
    humidity (%), and barometric pressure (hPa/kPa).
    """
    try:
        # Initialize BME280 sensor on I2C bus
        bme = BME280.BME280(i2c=i2c)
        
        if not bme:
            print("No BME280 device found")
            return None
        
        # Read all sensor values
        # BME280 library returns formatted strings with units
        temp = bme.temperature  # Format: "XX.XC"
        hum = bme.humidity      # Format: "XX.X%"
        pres = bme.pressure     # Format: "XXX.XhPa" or "XX.XkPa"
        
        # Feed watchdog during sensor read
        wdt.feed()
        
        # Log readings to serial console for debugging
        print(f"Temperature: {temp}")
        print(f"Humidity: {hum}")
        print(f"Pressure: {pres}")
        
        return SensorData(temp, hum, pres)
        
    except Exception as e:
        print(f"Sensor error: {e}")
        return None

# ============================================================================
# NETWORK FUNCTIONS
# ============================================================================

def connect_wifi():
    """
    Establishes WiFi connection with static IP configuration.
    
    Returns:
        bool: True if connected successfully, False otherwise
        
    Waits up to 15 seconds for connection, blinking LED to show progress.
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    # Configure static IP (prevents DHCP delays and ensures consistent address)
    wlan.ifconfig((STATIC_IP, SUBNET_MASK, GATEWAY_IP, DNS_SERVER))
    
    if not wlan.isconnected():
        print(f"Connecting to {config.wifi_ssid}...")
        wlan.connect(config.wifi_ssid, config.wifi_password)
        
        # Wait up to 15 seconds for connection with status indication
        for i in range(15):
            wdt.feed()  # Prevent watchdog reset during connection
            
            if wlan.isconnected():
                print(f"WiFi Connected. IP: {wlan.ifconfig()[0]}")
                signal_success()
                return True
            
            # Alternate LED on/off while connecting
            if i % 2 == 0:
                led.on()
            else:
                led.off()
            
            time.sleep(1)
        
        # Connection timeout
        print("WiFi connection failed")
        signal_error('wifi')
        led.off()
        return False
    
    # Already connected from previous attempt
    print("WiFi already connected")
    led.on()
    return True

def connect_mqtt():
    """
    Connects to MQTT broker with configured credentials.
    
    Returns:
        MQTTClient: Connected client object, or None if connection failed
    """
    try:
        client = MQTTClient(
            client_id=MQTT_CLIENT_ID,
            server=MQTT_SERVER,
            port=MQTT_PORT,
            user=MQTT_USER,
            password=MQTT_PASSWORD,
            keepalive=MQTT_KEEPALIVE,
            ssl=MQTT_SSL,
            ssl_params=MQTT_SSL_PARAMS
        )
        client.connect()
        print("MQTT Connected")
        signal_success()
        return client
        
    except Exception as e:
        print(f"MQTT Connection failed: {e}")
        signal_error('mqtt')
        led.off()
        return None

# ============================================================================
# MAIN PROGRAM LOOP
# ============================================================================

mqtt_client = None  # Global MQTT client reference

try:
    while True:
        try:
            wdt.feed()  # Reset watchdog timer every loop iteration
            
            # --- Step 1: Verify WiFi Connection ---
            if not network.WLAN(network.STA_IF).isconnected():
                print("WiFi disconnected, reconnecting...")
                led.off()
                mqtt_client = None  # Clear MQTT client on WiFi disconnect
                
                if not connect_wifi():
                    print("WiFi down, retrying in 10s...")
                    time.sleep(10)
                    continue  # Skip rest of loop, retry connection

            # --- Step 2: Verify MQTT Connection ---
            if mqtt_client is None:
                mqtt_client = connect_mqtt()
                if mqtt_client is None:
                    time.sleep(10)
                    continue  # Skip to next loop if MQTT connection failed

            # --- Step 3: Read Sensors and Publish Data ---
            readings = get_sensor_readings()
            
            if readings is not None:
                try:
                    # Verify broker is still responsive
                    mqtt_client.ping()
                    mqtt_client.check_msg()  # Process any incoming messages
                    
                    # Publish sensor data to separate MQTT topics
                    mqtt_client.publish(MQTT_TOPIC_TEMPERATURE, readings.temp)
                    mqtt_client.publish(MQTT_TOPIC_HUMIDITY, readings.hum)
                    mqtt_client.publish(MQTT_TOPIC_PRESSURE, readings.pres)
                    print(f"Published temp:{readings.temp} to {MQTT_TOPIC_TEMPERATURE}")
                    print(f"Published hum:{readings.hum} to {MQTT_TOPIC_HUMIDITY}")
                    print(f"Published pres:{readings.pres} to {MQTT_TOPIC_PRESSURE}")
                    
                    # Visual confirmation of successful transmission
                    signal_heartbeat()
                    
                except Exception as e:
                    # MQTT publish failed - force reconnection
                    print(f"MQTT publish error: {e}")
                    signal_error('mqtt')
                    mqtt_client = None
                    time.sleep(5)
                    continue
                    
            else:
                # Sensor reading failed - show error but maintain connections
                print("Sensor read failed")
                signal_error('sensor')
                led.on()  # Keep LED on to show WiFi/MQTT still connected

            # --- Step 4: Memory Management and Loop Delay ---
            gc.collect()  # Free unused memory (important for long-running MicroPython)
            
            # Sleep 9 seconds between readings, feeding watchdog during sleep
            for _ in range(9):
                wdt.feed()
                time.sleep(1)

        except Exception as e:
            # Catch-all for unexpected errors in main loop
            print(f"Unexpected error in main loop: {e}")
            signal_error('general')
            led.off()
            mqtt_client = None  # Force reconnection attempt
            time.sleep(5)

except KeyboardInterrupt:
    # Clean exit on Ctrl+C
    print("\nProgram stopped by user")
    
finally:
    # Cleanup on program exit
    led.off()
    if mqtt_client:
        try:
            mqtt_client.disconnect()
        except:
            pass  # Ignore disconnect errors during cleanup
    print("Cleanup complete, program ended")
```