"""Central notification worker tests."""

from threading import Event

import pytest

from pyhookkit.application.notification_worker import NotificationWorker


class StubRouter:
    def __init__(self, outcomes: list[bool]) -> None:
        self._outcomes = outcomes

    def deliver_next(self) -> bool:
        return self._outcomes.pop(0)


def test_worker_delivers_and_pauses_until_stopped() -> None:
    stop = Event()
    pauses: list[float] = []

    def pause(seconds: float) -> None:
        pauses.append(seconds)
        stop.set()

    NotificationWorker(
        StubRouter([True, False]),
        poll_interval_seconds=0.25,
        pause=pause,
    ).run(stop)

    assert pauses == [0.25]


def test_worker_rejects_non_positive_interval() -> None:
    with pytest.raises(ValueError, match="poll interval"):
        NotificationWorker(
            StubRouter([]),
            poll_interval_seconds=0,
        )
