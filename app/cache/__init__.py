import time


class MemoryCache:
    """Simple TTL-based in-memory cache."""

    def __init__(self, default_ttl: int = 300) -> None:
        self._default_ttl = default_ttl
        self._store: dict[str, tuple[float, object]] = {}

    async def get(self, key: str) -> object | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expiry, value = entry
        if time.monotonic() > expiry:
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: object, ttl: int | None = None) -> None:
        ttl = ttl if ttl is not None else self._default_ttl
        self._store[key] = (time.monotonic() + ttl, value)

    async def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    async def clear_expired(self) -> int:
        now = time.monotonic()
        expired = [k for k, (e, _) in self._store.items() if now > e]
        for k in expired:
            del self._store[k]
        return len(expired)

    @property
    def size(self) -> int:
        return len(self._store)
