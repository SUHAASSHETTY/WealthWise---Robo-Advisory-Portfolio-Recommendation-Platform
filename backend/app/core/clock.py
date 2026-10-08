"""Injectable clock (app_spec §5.2): domain and services never call date.today() / datetime.now() directly."""

import time
from datetime import UTC, date, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...

    def today(self) -> date: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(tz=UTC)

    def today(self) -> date:
        return self.now().date()


class FixedClock:
    """Deterministic clock for tests and simulations."""

    def __init__(self, at: datetime) -> None:
        self._at = at

    def now(self) -> datetime:
        return self._at

    def today(self) -> date:
        return self._at.date()


class AnchoredClock:
    """Starts at a pinned instant and advances in real time (WEALTHWISE_FIXED_CLOCK, app_spec §5.2).

    today() stays on the anchor date for evaluator/demo runs, while record timestamps remain strictly ordered.
    """

    def __init__(self, anchor: datetime) -> None:
        self._anchor = anchor
        self._started = time.perf_counter_ns()
        self._last = anchor

    def now(self) -> datetime:
        elapsed = timedelta(microseconds=(time.perf_counter_ns() - self._started) // 1000)
        candidate = self._anchor + elapsed
        self._last = candidate if candidate > self._last else self._last + timedelta(microseconds=1)
        return self._last

    def today(self) -> date:
        return self.now().date()
