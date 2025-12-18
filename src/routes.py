import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from src.database import get_current_status
from src.system_info import live_system_stats

router = APIRouter()


@router.get("/")
async def get_index():
    try:
        with open("static/index.html") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("index.html not found", status_code=404)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print(f"🔌 New Dashboard Connected: {websocket.client}")
    try:
        while True:
            db_data = get_current_status()
            await websocket.send_json({
                "sensors": db_data,
                "system": live_system_stats
            })
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print(f"🔌 Dashboard Disconnected")
    except Exception as e:
        print(f"⚠️ WS Error: {e}")
