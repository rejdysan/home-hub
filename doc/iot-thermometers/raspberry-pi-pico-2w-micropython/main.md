# Example for 'bedroom' thermometer
```python
import machine
import time
import network
import gc
from umqtt.simple import MQTTClient
import config
import onewire
import ds18x20

# Configuration to set static IP (not needed)
STATIC_IP = '192.168.0.X'
SUBNET_MASK = '255.255.255.0'
GATEWAY_IP = '192.168.0.X'
DNS_SERVER = '8.8.8.8'

# MQTT Parameters
MQTT_TOPIC_TEMPERATURE_BEDROOM = 'pico/temperature/bedroom'
MQTT_SERVER = config.mqtt_server
MQTT_PORT = 1883
MQTT_USER = config.mqtt_username
MQTT_PASSWORD = config.mqtt_password
MQTT_CLIENT_ID = b"raspberrypi_pico_bedroom"
MQTT_KEEPALIVE = 7200
MQTT_SSL = False   # set to False if using local Mosquitto MQTT broker
MQTT_SSL_PARAMS = {'server_hostname': MQTT_SERVER}

# DS18B20 Setup
ds_pin = machine.Pin(22)
ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))

def get_temperature():
    """Reads temperature from the DS18B20 sensor."""
    try:
        roms = ds_sensor.scan()
        if not roms:
            print("No DS18B20 devices found")
            return 999999 # returns unrealistic value
        
        ds_sensor.convert_temp()
        time.sleep_ms(750) # Required conversion time for DS18B20
        
        tempC = ds_sensor.read_temp(roms[0])
        print(f"Reading: {tempC:.2f} C")
        return tempC
    except Exception as e:
        print(f"Sensor error: {e}")
        return None

def connect_wifi():
    """Establishes Wi-Fi connection with static IP."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.ifconfig((STATIC_IP, SUBNET_MASK, GATEWAY_IP, DNS_SERVER)) # Set static IP address (not needed)
    
    if not wlan.isconnected():
        print(f"Connecting to {config.wifi_ssid}...")
        wlan.connect(config.wifi_ssid, config.wifi_password)
        
        # Wait up to 10 seconds for connection
        for _ in range(10):
            if wlan.isconnected():
                print(f"WiFi Connected. IP: {wlan.ifconfig()[0]}")
                return True
            time.sleep(1)
            
    return wlan.isconnected()

def connect_mqtt():
    """Connects to the MQTT broker."""
    try:
        client = MQTTClient(client_id=MQTT_CLIENT_ID,
                            server=MQTT_SERVER,
                            port=MQTT_PORT,
                            user=MQTT_USER,
                            password=MQTT_PASSWORD,
                            keepalive=MQTT_KEEPALIVE,
                            ssl=MQTT_SSL,
                            ssl_params=MQTT_SSL_PARAMS)
        client.connect()
        print("MQTT Connected")
        return client
    except Exception as e:
        print(f"MQTT Connection failed: {e}")
        return None

# --- Main Program Loop ---
mqtt_client = None

while True:
    try:
        # 1. Ensure WiFi is connected
        if not network.WLAN(network.STA_IF).isconnected():
            if not connect_wifi():
                print("WiFi down, retrying in 10s...")
                time.sleep(10)
                continue

        # 2. Ensure MQTT is connected
        if mqtt_client is None:
            mqtt_client = connect_mqtt()
            if mqtt_client is None:
                time.sleep(10)
                continue

        # 3. Read and Publish Data
        temp = get_temperature()
        if temp is not None:
            # check_msg() handles keep-alive and incoming messages
            mqtt_client.check_msg()
            mqtt_client.publish(MQTT_TOPIC_TEMPERATURE_BEDROOM, str(temp))
            print(f"Published {temp} to {MQTT_TOPIC_TEMPERATURE_BEDROOM}")

        # Memory management and loop delay
        gc.collect()
        time.sleep(10)

    except Exception as e:
        print(f"Unexpected error: {e}. Resetting connection...")
        mqtt_client = None # Force reconnection on next loop
        time.sleep(5)
```