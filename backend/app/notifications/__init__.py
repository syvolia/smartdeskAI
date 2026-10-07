"""Notification subsystem.

Architecture:

    Ticket domain ─► NotificationService ─┬─► InAppChannel   (DB)
                                          ├─► EmailChannel   (future)
                                          └─► WebSocketChannel (future)

The ticket domain only calls the service's typed `on_*()` methods. Adding
a delivery mechanism means adding a `NotificationChannel` implementation
and registering it — no changes to callers.
"""