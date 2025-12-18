import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from queue import Queue
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.config import config
from src.logger import logger
from src.database import init_db, close_all_connections
from src.mqtt_handler import setup_mqtt, set_sensor_callback, set_status_change_callback, get_sensor_status
from src.routes import router, update_weather_data, update_nameday_data, update_bus_data, check_sensor_status, update_todoist_data, close_http_client, cleanup_database_daily
from src.system_info import monitor_system, set_broadcast_func
from src.websocket_manager import manager
from src import sensor_cache

# Initialize MQTT client
mqttc = setup_mqtt()

# Store reference to the event loop for thread-safe callback
_main_loop = None

# Queue to store sensor updates if event loop is not ready (startup race condition protection)
_sensor_update_queue: Queue = Queue(maxsize=1000)


# --- BROADCAST HELPERS ---
async def broadcast_sensor_update(name: str, prop: str, val: float):
    """
    Broadcast sensor update to all connected WebSocket clients.

    OPTIMIZED: Uses in-memory cache instead of querying database on every update.
    This reduces SD card I/O significantly on Raspberry Pi.
    """
    # Update cache
    sensor_cache.update(name, prop, val)

    # Broadcast cached data (no DB query!)
    await manager.broadcast({"type": "sensors", "data": sensor_cache.get_all_as_dicts()})

    # Also broadcast updated sensor status
    await manager.broadcast({"type": "sensor_status", "data": get_sensor_status()})
    logger.debug(f"📡 Broadcasted sensor update: {name}/{prop} = {val}")


async def broadcast_status_change(name: str, is_online: bool):
    """Broadcast sensor status change to all connected WebSocket clients."""
    await manager.broadcast({
        "type": "sensor_status",
        "data": get_sensor_status()
    })
    status_str = "online" if is_online else "offline"
    logger.debug(f"📡 Broadcasted sensor status change: {name} is {status_str}")


def on_sensor_data(name: str, prop: str, val: float):
    """
    Callback when MQTT sensor data arrives (sync context from MQTT thread).

    Implements queue-based fallback to prevent data loss during startup race conditions.
    """
    global _main_loop

    if _main_loop is None:
        # Event loop not ready - queue the update for later processing
        try:
            _sensor_update_queue.put_nowait({
                "type": "sensor",
                "name": name,
                "prop": prop,
                "val": val
            })
            logger.debug(f"📦 Queued sensor update (event loop not ready): {name}/{prop} = {val}")
        except Exception as e:
            logger.error(f"❌ Failed to queue sensor update: {e}")
        return

    # Event loop ready - broadcast immediately
    asyncio.run_coroutine_threadsafe(
        broadcast_sensor_update(name, prop, val),
        _main_loop
    )


def on_sensor_status_change(name: str, is_online: bool):
    """
    Callback when sensor online/offline status changes (sync context from MQTT thread).

    Implements queue-based fallback to prevent data loss during startup race conditions.
    """
    global _main_loop

    if _main_loop is None:
        # Event loop not ready - queue the status change for later processing
        try:
            _sensor_update_queue.put_nowait({
                "type": "status",
                "name": name,
                "is_online": is_online
            })
            logger.debug(f"📦 Queued status change (event loop not ready): {name} is {'online' if is_online else 'offline'}")
        except Exception as e:
            logger.error(f"❌ Failed to queue status change: {e}")
        return

    # Event loop ready - broadcast immediately
    asyncio.run_coroutine_threadsafe(
        broadcast_status_change(name, is_online),
        _main_loop
    )


async def process_queued_updates():
    """
    Process any sensor updates that were queued during startup.

    This ONLY processes updates that arrived before the event loop was ready.
    Once processed, normal updates bypass the queue and go directly via
    asyncio.run_coroutine_threadsafe() for instant real-time updates.
    """
    if _sensor_update_queue.empty():
        logger.info("📦 No queued updates to process")
        return

    processed_count = 0
    logger.info(f"📦 Processing {_sensor_update_queue.qsize()} queued updates from startup...")

    while not _sensor_update_queue.empty():
        try:
            update = _sensor_update_queue.get_nowait()

            if update["type"] == "sensor":
                await broadcast_sensor_update(update["name"], update["prop"], update["val"])
                processed_count += 1
            elif update["type"] == "status":
                await broadcast_status_change(update["name"], update["is_online"])
                processed_count += 1

        except Exception as e:
            logger.error(f"⚠️ Error processing queued update: {e}", exc_info=True)

    logger.info(f"✅ Processed {processed_count} queued updates from startup")


# --- LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    global _main_loop
    tasks = []

    try:
        # [STARTUP] Initialize services
        logger.info("🚀 Starting Home Hub server...")

        # Capture the event loop for thread-safe callbacks from MQTT
        _main_loop = asyncio.get_running_loop()
        logger.info("✅ Event loop captured for MQTT callbacks")

        # Process any sensor updates that arrived before event loop was ready
        await process_queued_updates()

        # Set up broadcast callbacks
        set_broadcast_func(manager.broadcast)
        set_sensor_callback(on_sensor_data)
        set_status_change_callback(on_sensor_status_change)
        logger.info("✅ Broadcast callbacks configured")

        # Initialize database
        try:
            init_db()
            logger.info("✅ Database initialized")

            # Load sensor readings into cache
            sensor_cache.load_from_db()

        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise

        # Connect to MQTT broker
        try:
            mqttc.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=config.MQTT_KEEPALIVE)
            mqttc.loop_start()
            logger.info(f"✅ MQTT connected to {config.MQTT_BROKER}:{config.MQTT_PORT}")
        except Exception as e:
            logger.error(f"❌ MQTT connection failed: {e}")
            raise

        # Start background tasks
        try:
            tasks = [
                asyncio.create_task(monitor_system(), name="system_monitor"),
                asyncio.create_task(update_weather_data(), name="weather_update"),
                asyncio.create_task(update_nameday_data(), name="nameday_update"),
                asyncio.create_task(update_bus_data(), name="bus_update"),
                asyncio.create_task(check_sensor_status(), name="sensor_status_check"),
                asyncio.create_task(update_todoist_data(), name="todoist_update"),
                asyncio.create_task(cleanup_database_daily(), name="database_cleanup")
            ]
            logger.info("✅ Background tasks started")
        except Exception as e:
            logger.error(f"❌ Failed to start background tasks: {e}")
            raise

        logger.info("🚀 Server started successfully")

        yield  # The application runs here

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

    finally:
        # [SHUTDOWN] Cleanup
        logger.info("🛑 Shutting down server...")

        # Cancel all background tasks
        for task in tasks:
            if not task.done():
                task.cancel()
                logger.debug(f"Cancelled task: {task.get_name()}")

        # Wait for tasks to finish
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("✅ All background tasks stopped")

        # Stop MQTT
        try:
            mqttc.loop_stop()
            mqttc.disconnect()
            logger.info("✅ MQTT disconnected")
        except Exception as e:
            logger.warning(f"⚠️ MQTT disconnect error: {e}")

        # Close all WebSocket connections gracefully
        try:
            if manager.active_connections:
                logger.info(f"Closing {len(manager.active_connections)} WebSocket connections...")
                connections = list(manager.active_connections)
                for ws in connections:
                    try:
                        await ws.close(code=1001, reason="Server shutting down")
                    except Exception:
                        pass
                    manager.disconnect(ws)
                logger.info("✅ WebSocket connections closed")
        except Exception as e:
            logger.warning(f"⚠️ WebSocket close error: {e}")

        # Close HTTP client connections
        try:
            await close_http_client()
        except Exception as e:
            logger.warning(f"⚠️ HTTP client close error: {e}")

        # Close database connections
        try:
            close_all_connections()
            logger.info("✅ Database connections closed")
        except Exception as e:
            logger.warning(f"⚠️ Database close error: {e}")

        logger.info("🛑 Server shutdown complete")


app = FastAPI(
    title="Home Hub",
    description="IoT sensor monitoring and home automation hub",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware (restrictive for production security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:63343",  # PyCharm dev server
        # Add Raspberry Pi local network access if needed:
        # f"http://{config.HOST}:{config.PORT}",
    ],
    allow_credentials=True,
    # Only allow necessary HTTP methods (no PUT, DELETE, etc.)
    allow_methods=["GET", "POST"],
    # Only allow necessary headers
    allow_headers=["Content-Type", "Authorization"],
)

# Include the routes from our separate file
app.include_router(router)

# Mount static files (CSS, JS, etc.)
static_path = Path(__file__).resolve().parent / "src" / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level=config.LOG_LEVEL.lower()
    )
