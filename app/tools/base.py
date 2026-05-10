from dataclasses import dataclass, field
from collections.abc import Awaitable, Callable


@dataclass
class Tool:
    """A single tool that the agent can call via OpenAI function calling."""

    name: str
    description: str
    parameters: dict  # JSON Schema dict
    handler: Callable[..., Awaitable[dict]]
    cache_ttl: int | None = None  # None = no caching
