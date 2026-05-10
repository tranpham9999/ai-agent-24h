import httpx

from app.tools.base import Tool
from app.tools.registry import ToolRegistry

COORDINATES: dict[str, tuple[float, float]] = {
    "hanoi": (21.0278, 105.8342),
    "hà nội": (21.0278, 105.8342),
    "ho chi minh": (10.8231, 106.6297),
    "hồ chí minh": (10.8231, 106.6297),
    "saigon": (10.8231, 106.6297),
    "sài gòn": (10.8231, 106.6297),
    "thu duc": (10.8500, 106.7500),
    "thủ đức": (10.8500, 106.7500),
    "da nang": (16.0544, 108.2022),
    "đà nẵng": (16.0544, 108.2022),
    "new york": (40.7128, -74.0060),
    "london": (51.5074, -0.1278),
    "tokyo": (35.6762, 139.6503),
    "sydney": (-33.8688, 151.2093),
    "paris": (48.8566, 2.3522),
    "singapore": (1.3521, 103.8198),
    "seoul": (37.5665, 126.9780),
}


def _find_city(city: str) -> tuple[float, float] | None:
    """Flexibly find city coordinates (partial match, diacritics, comma-split)."""
    key = city.lower().strip()

    # 1. Exact match
    coord = COORDINATES.get(key)
    if coord:
        return coord

    # 2. Try each part (e.g. "Thu Duc, Ho Chi Minh" -> check "thu duc", "ho chi minh")
    parts = [p.strip() for p in key.replace(",", " ").split()]
    if len(parts) > 1:
        for i in range(len(parts)):
            for j in range(i + 1, len(parts) + 1):
                sub = " ".join(parts[i:j])
                coord = COORDINATES.get(sub)
                if coord:
                    return coord

    # 3. Try matching any key contained in the input
    for name, coord in COORDINATES.items():
        if name in key or key in name:
            return coord

    return None


async def _get_weather(city: str = "hanoi") -> dict:
    city_key = city.lower().strip()
    coord = _find_city(city_key)
    if not coord:
        return {"success": False, "error": f"Không tìm thấy thành phố: {city}"}

    lat, lon = coord
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current_weather=true&timezone=auto"
    )

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

    current = data.get("current_weather", {})
    return {
        "success": True,
        "data": {
            "city": city,
            "temperature_c": current.get("temperature"),
            "windspeed_kmh": current.get("windspeed"),
            "weather_code": current.get("weathercode"),
            "unit": "celsius",
        },
    }


def register(registry: ToolRegistry) -> None:
    registry.register(
        Tool(
            name="get_weather",
            description="Get current weather for a city (free, no API key needed)",
            parameters={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "City name (e.g. Hanoi, Ho Chi Minh, New York, London)",
                    }
                },
                "required": ["city"],
            },
            handler=_get_weather,
            cache_ttl=600,
        )
    )
