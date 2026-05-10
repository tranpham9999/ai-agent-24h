import httpx
from lxml import html

from app.tools.base import Tool
from app.tools.registry import ToolRegistry


async def _get_gold_price_vn() -> dict:
    """Get Vietnamese domestic gold prices (SJC, PNJ, DOJI) in VND."""
    url = "https://webgia.com/gia-vang/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, timeout=15, follow_redirects=True)
        resp.raise_for_status()

    tree = html.fromstring(resp.text)

    prices = []
    seen = set()
    table = tree.xpath("//table[1]")
    if table:
        for row in table[0].xpath(".//tr"):
            cells = [c.text_content().strip() for c in row.xpath(".//td")]
            if len(cells) >= 3:
                name = cells[0]
                buy = cells[1]
                sell = cells[2]
                # Only keep rows with actual numeric prices
                if ("000" in buy or "000" in sell) and buy != sell:
                    key = f"{name}|{buy}|{sell}"
                    if key not in seen:
                        seen.add(key)
                        prices.append({
                            "name": name,
                            "buy_vnd": buy,
                            "sell_vnd": sell,
                        })

    return {"success": True, "data": prices}


def register(registry: ToolRegistry) -> None:
    registry.register(
        Tool(
            name="get_gold_price_vn",
            description="Get Vietnamese domestic gold prices (SJC, PNJ, DOJI, etc.) in VND",
            parameters={"type": "object", "properties": {}},
            handler=_get_gold_price_vn,
            cache_ttl=300,
        )
    )
