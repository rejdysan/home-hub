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
from typing import Dict, Any

# --- MQTT CREDENTIALS ---
# Use one of the usernames/passwords already in your /etc/mosquitto/passwd
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_USER = "home_hub_admin"
MQTT_PASS = "home_hub_admin1234"
DB_NAME = "sensors.db"

# GLOBAL LIVE STORAGE (Memory only - avoids DB bloat)
live_system_stats: Dict[str, Any] = {
    "cpu": 0.0,
    "ram_pct": 0.0,
    "ram_used": 0.0,
    "ram_total": 0.0,
    "disk_pct": 0.0,
    "disk_used": 0.0,
    "disk_total": 0.0,
    "net_sent": 0.0,
    "net_recv": 0.0
}


# --- SYSTEM MONITOR ---
async def monitor_system():
    last_net_io = psutil.net_io_counters()
    last_net_time = time.time()

    while True:
        try:
            # CPU & RAM (These are standard across all OS)
            live_system_stats["cpu"] = psutil.cpu_percent(interval=1)
            vm = psutil.virtual_memory()
            live_system_stats["ram_total"] = round(vm.total / (1024 ** 3), 1)
            live_system_stats["ram_used"] = round((vm.total - vm.available) / (1024 ** 3), 1)
            live_system_stats["ram_pct"] = vm.percent

            # --- SAFE TEMPERATURE CHECK ---
            # Not all systems (especially Mac/Windows) support this via psutil
            try:
                if hasattr(psutil, "sensors_temperatures"):
                    temps = psutil.sensors_temperatures()
                    if temps and 'cpu_thermal' in temps:
                        live_system_stats["cpu_temp"] = temps['cpu_thermal'][0].current
                    elif temps and 'coretemp' in temps:
                        live_system_stats["cpu_temp"] = temps['coretemp'][0].current
                    else:
                        live_system_stats["cpu_temp"] = None
                else:
                    live_system_stats["cpu_temp"] = None
            except Exception:
                live_system_stats["cpu_temp"] = None

            # --- NETWORK & DISK (Wrapped in safety) ---
            try:
                curr_io = psutil.net_io_counters()
                curr_time = time.time()
                elapsed = curr_time - last_net_time
                live_system_stats["net_sent"] = round((curr_io.bytes_sent - last_net_io.bytes_sent) / elapsed / 1024, 1)
                live_system_stats["net_recv"] = round((curr_io.bytes_recv - last_net_io.bytes_recv) / elapsed / 1024, 1)
                last_net_io, last_net_time = curr_io, curr_time
            except:
                pass

            # Smart Disk
            path = '/'
            for p in psutil.disk_partitions():
                if p.mountpoint == '/System/Volumes/Data':
                    path = '/System/Volumes/Data';
                    break
            usage = psutil.disk_usage(path)
            live_system_stats["disk_total"] = round(usage.total / (1024 ** 3), 1)
            live_system_stats["disk_used"] = round(usage.used / (1024 ** 3), 1)
            live_system_stats["disk_pct"] = usage.percent

        except Exception as e:
            # This catch-all ensures the loop NEVER dies
            print(f"⚠️ Internal Monitor Warning: {e}")

        await asyncio.sleep(2)


# --- LIFESPAN ---
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


# --- DATABASE ---
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS reading (id INTEGER PRIMARY KEY AUTOINCREMENT, sensor TEXT, property TEXT, temp REAL, ts DATETIME DEFAULT CURRENT_TIMESTAMP)")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS current_status (sensor TEXT, property TEXT, temp REAL, ts DATETIME, PRIMARY KEY (sensor, property))")
        conn.execute("""
                     CREATE TRIGGER IF NOT EXISTS update_current_status AFTER INSERT ON reading
                     BEGIN
                     INSERT INTO current_status (sensor, property, temp, ts)
                     VALUES (NEW.sensor, NEW.property, NEW.temp, NEW.ts) ON CONFLICT(sensor, property) DO
                     UPDATE SET temp = excluded.temp, ts = excluded.ts;
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
        parts = msg.topic.split('/')
        prop, name = parts[-2], parts[-1]
        val = float(msg.payload.decode())

        if (time.time() - last_save_time.get((name, prop), 0)) < 5: return
        last_save_time[(name, prop)] = time.time()

        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("INSERT INTO reading (sensor, property, temp) VALUES (?, ?, ?)", (name, prop, val))
            conn.commit()
        print(f"💾 Saved: {name} [{prop}] -> {val}°C, at {datetime.datetime.now()}")
    except Exception as e:
        print(f"⚠️ MQTT Error: {e}")


# --- MQTT CLIENT CONFIG ---
mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqttc.username_pw_set(MQTT_USER, MQTT_PASS)
mqttc.on_connect = on_connect
mqttc.on_message = on_message

# This is the "Magic" reconnection line:
# min_delay: wait 1s after first fail
# max_delay: never wait more than 120s between attempts
mqttc.reconnect_delay_set(min_delay=1, max_delay=120)

# Inside your lifespan startup:
# .loop_start() runs a background thread that handles
# automatic reconnections for you.
mqttc.loop_start()


# --- ROUTES ---
@app.get("/")
async def get():
    with open("index.html") as f:
        return HTMLResponse(f.read())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(f"🔌 New Dashboard Connected: {websocket.client}")
    try:
        while True:
            with sqlite3.connect(DB_NAME) as conn:
                # Super fast: reading from a table that only has ~3-6 rows
                cursor = conn.execute("SELECT sensor, property, temp, ts FROM current_status")
                db_data = [{"sensor": r[0], "prop": r[1], "temp": r[2], "ts": r[3]} for r in cursor.fetchall()]
            await websocket.send_json({"sensors": db_data, "system": live_system_stats})
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        # This is vital: it cleans up memory when a user closes the tab
        print(f"🔌 Dashboard Disconnected: {websocket.client}")
    except Exception as e:
        print(f"⚠️ WS Error: {e}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
