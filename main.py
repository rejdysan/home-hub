import sqlite3
import time
import datetime
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import paho.mqtt.client as mqtt
import uvicorn
import psutil

# --- MQTT CREDENTIALS ---
# Use one of the usernames/passwords already in your /etc/mosquitto/passwd
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_USER = "home_hub_admin"
MQTT_PASS = "home_hub_admin1234"
DB_NAME = "sensors.db"


async def monitor_system():
    while True:
        try:
            # 1. CPU: Standard 0-100% (averaged over all cores)
            # interval=1 is important for accuracy
            cpu_pct = psutil.cpu_percent(interval=1)

            # 2. RAM: Let's calculate "App Memory" like a Pro
            vm = psutil.virtual_memory()
            # On Mac/Linux: Available is more accurate than 'Free'
            total_gb = round(vm.total / (1024 ** 3), 1)
            # Available memory is what's truly left for apps
            used_gb = round((vm.total - vm.available) / (1024 ** 3), 1)
            ram_pct = vm.percent

            # 3. Disk: Focus on the main partition
            disk = psutil.disk_usage('/')
            d_total = round(disk.total / (1024 ** 3), 1)
            d_used = round(disk.used / (1024 ** 3), 1)
            d_pct = disk.percent

            stats = [
                ("System", "CPU Usage %", cpu_pct),
                ("System", "RAM Usage %", ram_pct),
                ("System", "RAM Used GB", used_gb),
                ("System", "RAM Total GB", total_gb),
                ("System", "Disk Usage %", d_pct),
                ("System", "Disk Used GB", d_used),
                ("System", "Disk Total GB", d_total)
            ]

            with sqlite3.connect(DB_NAME) as conn:
                for sensor, prop, val in stats:
                    conn.execute(
                        "INSERT INTO reading (sensor, property, temp) VALUES (?, ?, ?)",
                        (sensor, prop, val)
                    )
                conn.commit()

        except Exception as e:
            print(f"⚠️ Monitor Error: {e}")

        await asyncio.sleep(5)

# --- LIFESPAN MANAGER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # [STARTUP] Logic goes here
    init_db()
    mqttc.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    mqttc.loop_start()
    print("🚀 Server started: MQTT and DB initialized")

    # Start the system monitor in the background
    monitor_task = asyncio.create_task(monitor_system())

    yield  # The application runs here

    # [SHUTDOWN] Logic goes here
    monitor_task.cancel()
    mqttc.loop_stop()
    mqttc.disconnect()
    print("🛑 Server shutting down: Connections closed")


app = FastAPI(lifespan=lifespan)

# --- GLOBAL TRACKER ---
last_save_time = {}


# --- DATABASE SETUP ---
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        # 1. Historical table
        conn.execute("""
                     CREATE TABLE IF NOT EXISTS reading
                     (
                         id
                         INTEGER
                         PRIMARY
                         KEY
                         AUTOINCREMENT,
                         sensor
                         TEXT,
                         property
                         TEXT,
                         temp
                         REAL,
                         ts
                         DATETIME
                         DEFAULT
                         CURRENT_TIMESTAMP
                     )
                     """)

        # 2. Current Status table (The "Cheat Sheet" for the Dashboard)
        conn.execute("""
                     CREATE TABLE IF NOT EXISTS current_status
                     (
                         sensor
                         TEXT,
                         property
                         TEXT,
                         temp
                         REAL,
                         ts
                         DATETIME,
                         PRIMARY
                         KEY
                     (
                         sensor,
                         property
                     )
                         )
                     """)

        # 3. The Trigger: Automatically updates current_status after an INSERT into reading
        conn.execute("""
                     CREATE TRIGGER IF NOT EXISTS update_current_status
            AFTER INSERT ON reading
                     BEGIN
                     INSERT INTO current_status (sensor, property, temp, ts)
                     VALUES (NEW.sensor, NEW.property, NEW.temp, NEW.ts) ON CONFLICT(sensor, property) DO
                     UPDATE SET
                         temp = excluded.temp,
                         ts = excluded.ts;
                     END
                     """)
        conn.commit()


# --- MQTT CALLBACKS ---
def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print("✅ MQTT Connected")
        client.subscribe("pico/+/+")
    else:
        print(f"❌ MQTT Fail: {reason_code}")


def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        parts = msg.topic.split('/')
        sensor_property = parts[-2]
        sensor_name = parts[-1]
        temp_val = float(payload)

        current_time = time.time()
        tracking_key = (sensor_name, sensor_property)

        # Debounce logic: 5-second gate per sensor property
        if (current_time - last_save_time.get(tracking_key, 0)) < 5:
            return

        last_save_time[tracking_key] = current_time

        with sqlite3.connect(DB_NAME) as conn:
            conn.execute(
                "INSERT INTO reading (sensor, property, temp) VALUES (?, ?, ?)",
                (sensor_name, sensor_property, temp_val)
            )
            conn.commit()
        print(f"💾 Saved: {sensor_name} [{sensor_property}] -> {temp_val}°C, at {datetime.datetime.now()}")
    except Exception as e:
        print(f"⚠️ Error: {e}")


# --- MQTT CLIENT CONFIG ---
mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.username_pw_set(MQTT_USER, MQTT_PASS)
mqttc.on_connect = on_connect
mqttc.on_message = on_message
mqttc.reconnect_delay_set(min_delay=1, max_delay=120)


# --- ROUTES ---
@app.get("/")
async def get():
    with open("index.html") as f:
        return HTMLResponse(f.read())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            with sqlite3.connect(DB_NAME) as conn:
                # Super fast: reading from a table that only has ~3-6 rows
                cursor = conn.execute("SELECT sensor, property, temp, ts FROM current_status")
                data = [{"sensor": r[0], "prop": r[1], "temp": r[2], "ts": r[3]} for r in cursor.fetchall()]

            await websocket.send_json(data)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
