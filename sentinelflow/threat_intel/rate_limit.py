"""Simple process-local rate limiter for free-tier APIs."""

from __future__ import annotations

import time


class RateLimiter:
    """Allow at most `max_calls` in each `per_seconds` window."""

    def __init__(self, max_calls: int = 4, per_seconds: float = 60.0):
        self.max_calls = max_calls
        self.per_seconds = per_seconds
        self._timestamps: list[float] = []

    def wait(self) -> None:
        now = time.time()
        self._timestamps = [t for t in self._timestamps if now - t < self.per_seconds]
        if len(self._timestamps) >= self.max_calls:
            sleep_for = self.per_seconds - (now - self._timestamps[0]) + 0.05
            if sleep_for > 0:
                time.sleep(sleep_for)
            now = time.time()
            self._timestamps = [t for t in self._timestamps if now - t < self.per_seconds]
        self._timestamps.append(time.time())
