from app.tools.base import Tool
from app.tools.registry import ToolRegistry

COINGECKO_IDS: dict[str, str] = {
    "btc": "bitcoin",
    "bitcoin": "bitcoin",
    "eth": "ethereum",
    "ethereum": "ethereum",
    "sol": "solana",
    "solana": "solana",
    "bnb": "binancecoin",
    "xrp": "ripple",
    "ada": "cardano",
    "doge": "dogecoin",
    "dot": "polkadot",
}


async def _get_crypto_price(coins: list[str] | None = None) -> dict:
    import httpx

    if not coins:
        coins = ["btc", "eth", "sol"]

    ids = []
    for c in coins:
        normalized = COINGECKO_IDS.get(c.lower().strip(), c.lower().strip())
        ids.append(normalized)

    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": ",".join(ids), "vs_currencies": "usd", "include_24hr_change": "true"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=15)
        if resp.status_code == 429:
            return {"success": False, "error": "Rate limited by CoinGecko"}
        resp.raise_for_status()
        data = resp.json()

    results = {}
    for coin_id, info in data.items():
        results[coin_id] = {
            "price_usd": info.get("usd"),
            "change_24h_percent": info.get("usd_24h_change"),
        }

    return {"success": True, "data": results}


def register(registry: ToolRegistry) -> None:
    registry.register(
        Tool(
            name="get_crypto_price",
            description="Get current cryptocurrency prices in USD",
            parameters={
                "type": "object",
                "properties": {
                    "coins": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of coin symbols: btc, eth, sol, bnb, xrp, ada, doge, dot",
                    }
                },
            },
            handler=_get_crypto_price,
            cache_ttl=120,
        )
    )
