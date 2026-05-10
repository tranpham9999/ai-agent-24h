import os
from datetime import datetime

SYSTEM_PROMPT = """You are AI Agent 24/7, an automated briefing assistant.

You have access to tools that can fetch real-time data and send messages.

CRITICAL: You MUST call tools for ANY factual information you need.
- Weather → call get_weather
- News/search → call web_search
- Gold prices → call get_gold_price_vn
- Crypto prices → call get_crypto_price
- Sending message → call send_message
NEVER answer from your training data when a tool can provide current data.

Follow this process for every request:
1. Decide what information you need
2. Call the appropriate tools (you can call MULTIPLE tools in parallel)
3. Wait for all tool results
4. Synthesize a clear, concise response
5. Send the response via the send_message tool

IMPORTANT: If a tool returns an error (e.g. API key not configured), rely on other tools that succeeded and note what's missing.

IMPORTANT: Always respond in Vietnamese (tiếng Việt).

Current date and time: {current_datetime}
User timezone: {timezone}
"""


def build_system_prompt(timezone: str = "Asia/Ho_Chi_Minh") -> str:
    return SYSTEM_PROMPT.format(
        current_datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        timezone=timezone,
    )


BRIEFING_MORNING = (
    "Tổng hợp bản tin buổi sáng: "
    "Top 5 tin công nghệ hôm nay, giá vàng thế giới, "
    "giá Bitcoin và top crypto biến động mạnh. "
    "Thời tiết hôm nay ở Hanoi. Gửi qua Telegram."
)

BRIEFING_MIDDAY = (
    "Midday check: tin tức nổi bật từ sáng đến giờ, "
    "giá vàng và crypto cập nhật. Gửi qua Telegram."
)

BRIEFING_EVENING = (
    "Tổng hợp buổi tối: tin tức trong ngày, "
    "giá vàng chốt ngày, crypto biến động. "
    "Thời tiết ngày mai ở Hanoi. Gửi qua Telegram."
)
