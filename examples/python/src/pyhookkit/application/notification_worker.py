"""Polling worker for queued central router deliveries."""

from collections.abc import Callable
from threading import Event
from time import sleep
from typing import Protocol


class NotificationWorkQueue(Protocol):
    """Expose one unit of queued notification work."""

    def deliver_next(self) -> bool:
        """Return whether one queued target was delivered."""
        ...


class NotificationWorker:
    """Drain queued deliveries with bounded idle polling."""

    def __init__(
        self,
        router: NotificationWorkQueue,
        *,
        poll_interval_seconds: float = 1.0,
        pause: Callable[[float], None] = sleep,
    ) -> None:
        if poll_interval_seconds <= 0:
            raise ValueError("worker poll interval must be positive")
        self._router = router
        self._poll_interval_seconds = poll_interval_seconds
        self._pause = pause

    def run(self, stop: Event) -> None:
        """Deliver until the caller requests shutdown."""
        while not stop.is_set():
            if not self._router.deliver_next():
                self._pause(self._poll_interval_seconds)
