import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn

from src.database import init_db
from src.mqtt_handler import setup_mqtt, MQTT_BROKER, MQTT_PORT
from src.routes import router
from src.system_info import monitor_system

mqttc = setup_mqtt()


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

# Include the routes from our separate file
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
