from fastapi import WebSocket
from typing import Dict, Set
import asyncio

class ConnectionManager:
    def __init__(self):
        # symbol -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, symbol: str):
        await websocket.accept()
        symbol = symbol.upper()
        if symbol not in self.active_connections:
            self.active_connections[symbol] = set()
        self.active_connections[symbol].add(websocket)

    def disconnect(self, websocket: WebSocket, symbol: str):
        symbol = symbol.upper()
        if symbol in self.active_connections:
            self.active_connections[symbol].discard(websocket)
            if not self.active_connections[symbol]:
                del self.active_connections[symbol]

    async def broadcast_price(self, symbol: str, price: float):
        symbol = symbol.upper()
        if symbol not in self.active_connections:
            return
        message = f"{price:.2f}"
        for connection in list(self.active_connections[symbol]):
            try:
                await connection.send_text(message)
            except Exception:
                # Remove dead connection
                self.disconnect(connection, symbol)

manager = ConnectionManager()