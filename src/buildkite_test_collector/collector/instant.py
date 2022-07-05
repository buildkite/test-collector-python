"""An instant of the monotonic clock"""

from dataclasses import dataclass
from datetime import timedelta

import time


@dataclass(frozen=True, order=True)
class Instant:
    """
    A wrapper around monotonic time.

    Due to the fact that the wall clock time can change while the system is
    running we use `time.monotonic()` to allow us to accurately measure relative
    times.
    """
    seconds: float

    def __add__(self, other: timedelta) -> 'Instant':
        """Add a timedelta to an instant to return a new instant"""
        if isinstance(other, timedelta):
            return Instant(seconds=self.seconds + other.total_seconds())

        return NotImplemented

    def __sub__(self, other: 'Instant') -> timedelta:
        """Subtract two instants returning a timedelta"""
        if isinstance(other, Instant):
            return timedelta(seconds=self.seconds - other.seconds)

        return NotImplemented

    @classmethod
    def now(cls) -> 'Instant':
        """Create a new instant with the current monotonic time"""
        return cls(seconds=time.monotonic())
