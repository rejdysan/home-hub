import asyncio
import json
from typing import Set
from fastapi import WebSocket, WebSocketException, status
from src.logger import logger

class WebSocketManager:
    # Maximum concurrent WebSocket connections for Raspberry Pi resource management
    MAX_CONNECTIONS = 10

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()  # Protect concurrent access to active_connections

    async def connect(self, websocket: WebSocket):
        """
        Accept and store a new WebSocket connection.

        Raises:
            WebSocketException: If maximum connection limit is reached
        """
        async with self._lock:
            # Check connection limit
            if len(self.active_connections) >= self.MAX_CONNECTIONS:
                logger.warning(f"⚠️ Max WebSocket connections ({self.MAX_CONNECTIONS}) reached, rejecting new connection")
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Maximum connections reached")
                raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Maximum connections reached")

            await websocket.accept()
            self.active_connections.add(websocket)
            client_info = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "unknown"
            logger.info(f"🔌 Dashboard connected: {client_info} (Total: {len(self.active_connections)}/{self.MAX_CONNECTIONS})")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection. Note: This is sync to allow cleanup in exception handlers."""
        self.active_connections.discard(websocket)
        logger.info(f"🔌 Dashboard disconnected (Total: {len(self.active_connections)}/{self.MAX_CONNECTIONS})")

    async def broadcast(self, data: dict):
        """
        Send data to all connected clients.

        Performance optimization: Serialize JSON once instead of per-client.
        """
        if not self.active_connections:
            return

        # Serialize JSON once (optimization for Raspberry Pi)
        json_data = json.dumps(data)

        # Get snapshot of connections under lock
        async with self._lock:
            connections = list(self.active_connections)

        # Broadcast outside lock to avoid blocking new connections
        disconnected = []
        for connection in connections:
            try:
                await connection.send_text(json_data)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected.append(connection)

        # Clean up failed connections
        for conn in disconnected:
            self.disconnect(conn)

# Global manager instance
manager = WebSocketManager()
