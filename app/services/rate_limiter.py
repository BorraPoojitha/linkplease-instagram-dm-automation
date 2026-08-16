import asyncio
import time
from collections import deque
from app.config import settings


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int = 10, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire_slot(self) -> float:
        """
        Attempts to acquire a slot for a send request.
        Returns the delay in seconds if rate limited, or 0.0 if slot acquired.
        If delay > 0, caller should wait delay seconds or postpone job.
        """
        async with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds

            # Prune timestamps outside the rolling window
            while self.timestamps and self.timestamps[0] <= cutoff:
                self.timestamps.popleft()

            if len(self.timestamps) < self.max_requests:
                self.timestamps.append(now)
                return 0.0
            else:
                # Calculate time to wait until oldest timestamp expires out of window
                oldest = self.timestamps[0]
                wait_time = max(0.01, (oldest + self.window_seconds) - now)
                return wait_time


# Shared rate limiter instance
rate_limiter = SlidingWindowRateLimiter(
    max_requests=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS
)
