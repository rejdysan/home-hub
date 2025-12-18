import os
import time
import datetime
import paho.mqtt.client as mqtt
from src.database import save_reading
from dotenv import load_dotenv

# Load the variables from the .env file
load_dotenv()

# Fetch variables using os.getenv(KEY, DEFAULT_VALUE)
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER = os.getenv("MQTT_USER")
MQTT_PASS = os.getenv("MQTT_PASS")

last_save_time = {}

def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print("✅ MQTT Connected")
        client.subscribe("pico/+/+")
    else:
        print(f"❌ MQTT Fail: {reason_code}")


def on_message(client, userdata, msg):
    try:
        parts = msg.topic.split('/')
        prop, name = parts[-2], parts[-1]
        val = float(msg.payload.decode())

        # Throttle saving to DB (5-second window)
        current_time = time.time()
        if (current_time - last_save_time.get((name, prop), 0)) < 5:
            return

        last_save_time[(name, prop)] = current_time
        save_reading(name, prop, val)
        print(f"💾 Saved: {name} [{prop}] -> {val}°C, at {datetime.datetime.now()}")
    except Exception as e:
        print(f"⚠️ MQTT Error: {e}")


def setup_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=120)
    return client
