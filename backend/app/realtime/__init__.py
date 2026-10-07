"""Real-time event delivery over WebSockets.

Shape:

    Ticket / Notification domain
              │
              ▼
    RealtimeBus.publish(event)
              │
       ┌──────┴──────┐
       ▼             ▼
   Local fanout  Redis pub/sub
   (this process) (other processes)

    WebSocket client ──── ConnectionManager.broadcast(event)
"""

from app.realtime.bus import RealtimeBus, get_realtime_bus
from app.realtime.manager import ConnectionManager, get_connection_manager
from app.realtime.schemas import EventType, RealtimeEvent

__all__ = [
    "ConnectionManager",
    "EventType",
    "RealtimeBus",
    "RealtimeEvent",
    "get_connection_manager",
    "get_realtime_bus",
]