"""Token-bucket rate limiter (per-user, in-memory)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class _Bucket:
    tokens: float
    last_refill: float
    capacity: float
    refill_rate: float  # tokens per second

    def try_consume(self, amount: float = 1.0) -> bool:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False

    @property
    def wait_seconds(self) -> float:
        """Estimated seconds until 1 token is available."""
        if self.tokens >= 1:
            return 0.0
        return (1 - self.tokens) / self.refill_rate


class RateLimiter:
    """Per-user dual token-bucket limiter (RPM + TPM).

    Parameters:
        rpm: max requests per minute
        tpm: max tokens per minute
    """

    def __init__(self, rpm: int = 60, tpm: int = 100_000):
        self.rpm = rpm
        self.tpm = tpm
        self._request_buckets: Dict[str, _Bucket] = {}
        self._token_buckets: Dict[str, _Bucket] = {}

    def _get_request_bucket(self, user_id: str) -> _Bucket:
        if user_id not in self._request_buckets:
            self._request_buckets[user_id] = _Bucket(
                tokens=float(self.rpm),
                last_refill=time.monotonic(),
                capacity=float(self.rpm),
                refill_rate=self.rpm / 60.0,
            )
        return self._request_buckets[user_id]

    def _get_token_bucket(self, user_id: str) -> _Bucket:
        if user_id not in self._token_buckets:
            self._token_buckets[user_id] = _Bucket(
                tokens=float(self.tpm),
                last_refill=time.monotonic(),
                capacity=float(self.tpm),
                refill_rate=self.tpm / 60.0,
            )
        return self._token_buckets[user_id]

    def check_request(self, user_id: str = "default") -> bool:
        """Check if user can make another request (RPM bucket)."""
        return self._get_request_bucket(user_id).try_consume(1.0)

    def check_tokens(self, user_id: str = "default", token_count: int = 0) -> bool:
        """Check if user can consume `token_count` tokens (TPM bucket)."""
        if token_count <= 0:
            return True
        return self._get_token_bucket(user_id).try_consume(float(token_count))

    def consume(self, user_id: str = "default", token_count: int = 0) -> bool:
        """Consume one request + N tokens. Returns False if rate-limited."""
        if not self.check_request(user_id):
            return False
        if token_count > 0 and not self.check_tokens(user_id, token_count):
            return False
        return True

    def wait_time(self, user_id: str = "default") -> float:
        """Return seconds until next request is allowed."""
        return self._get_request_bucket(user_id).wait_seconds
