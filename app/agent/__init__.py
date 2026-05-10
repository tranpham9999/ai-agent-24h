import json

from openai import AsyncOpenAI

from app.agent.prompts import build_system_prompt
from app.cache import MemoryCache
from app.config import Settings
from app.messaging.telegram import TelegramClient
from app.storage.database import Database
from app.tools.registry import ToolRegistry


class AgentCore:
    """LLM-driven agent loop: think → call tools → synthesize → respond."""

    def __init__(
        self,
        registry: ToolRegistry,
        openai_client: AsyncOpenAI,
        cache: MemoryCache,
        settings: Settings,
        telegram_client: TelegramClient | None = None,
        db: Database | None = None,
    ) -> None:
        self._registry = registry
        self._openai = openai_client
        self._cache = cache
        self._settings = settings
        self._telegram = telegram_client
        self._db = db
        self._model = settings.llm_model

    async def run(
        self,
        user_input: str,
        timezone: str = "Asia/Ho_Chi_Minh",
        platform_context: dict | None = None,
    ) -> str:
        """Execute one agent turn with optional platform context.

        ``platform_context`` carries:
        - ``{"platform": "telegram", "chat_id": "67890"}``
        """
        messages: list[dict] = [
            {"role": "system", "content": build_system_prompt(timezone=timezone)},
        ]

        # Load conversation history if platform context is available
        if platform_context and self._db:
            history = await self._db.get_conversation_history(
                platform=platform_context["platform"],
                channel_id=platform_context.get("channel_id") or platform_context.get("chat_id", ""),
            )
            for msg in history:
                messages.append(msg)

        messages.append({"role": "user", "content": user_input})

        response = await self._openai.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=self._registry.list_openai_specs(),
            tool_choice="required",
        )

        message = response.choices[0].message

        # If LLM didn't call any tool, return its text directly
        if not message.tool_calls:
            final_text = message.content or "Xin lỗi, tôi không thể xử lý yêu cầu này ngay bây giờ."
            await self._save_conversation(platform_context, user_input, final_text)
            await self._auto_reply(platform_context, final_text)
            return final_text

        # Append assistant message with tool_calls
        msg_entry: dict = {"role": "assistant", "content": message.content}
        msg_entry["tool_calls"] = [t.model_dump() for t in message.tool_calls]
        messages.append(msg_entry)

        # Execute all tool calls in parallel
        tool_results = await self._execute_tool_calls(message.tool_calls, platform_context)

        # Append each result
        for result in tool_results:
            messages.append(result)

        # Short-circuit: if the only tool was 'respond', extract message and skip synthesis
        respond_only = (
            len(message.tool_calls) == 1
            and message.tool_calls[0].function.name == "respond"
        )
        if respond_only:
            raw_args = message.tool_calls[0].function.arguments
            try:
                kwargs = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                kwargs = {}
            final_text = kwargs.get("message", "") or ""
            await self._save_conversation(platform_context, user_input, final_text)
            await self._auto_reply(platform_context, final_text)
            return final_text

        # Final LLM call to synthesize
        final = await self._openai.chat.completions.create(
            model=self._model,
            messages=messages,
        )

        final_text = final.choices[0].message.content or ""
        await self._save_conversation(platform_context, user_input, final_text)
        # Only auto-reply if no send_message tool was called (avoid double-send)
        has_send_message = any(
            tc.function.name == "send_message" for tc in message.tool_calls
        )
        if not has_send_message:
            await self._auto_reply(platform_context, final_text)
        return final_text

    async def _auto_reply(self, platform_context: dict | None, text: str) -> None:
        """Send text back to the platform if no send_message was called."""
        if not platform_context or not self._telegram:
            return
        plat = platform_context.get("platform", "")
        if plat == "telegram":
            chat_id = platform_context.get("chat_id", "")
            if chat_id:
                try:
                    await self._telegram.send_message(chat_id, text)
                except Exception:
                    pass

    async def _save_conversation(
        self, platform_context: dict | None, user_input: str, response: str
    ) -> None:
        if not platform_context or not self._db:
            return
        plat = platform_context["platform"]
        cid = platform_context.get("channel_id") or platform_context.get("chat_id", "")
        await self._db.save_conversation(plat, cid, "user", user_input)
        await self._db.save_conversation(plat, cid, "assistant", response)

    async def _execute_tool_calls(
        self, tool_calls: list[object], platform_context: dict | None = None
    ) -> list[dict]:
        """Execute all tool calls in parallel and return result messages."""
        import asyncio

        async def call_one(tc: object) -> dict:
            tc_id = str(tc.id)  # type: ignore[attr-defined]
            func_name = str(tc.function.name)  # type: ignore[attr-defined]
            raw_args = tc.function.arguments  # type: ignore[attr-defined]

            try:
                kwargs = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                kwargs = {}

            # Inject platform routing into send_message calls
            if func_name == "send_message" and platform_context:
                plat = platform_context.get("platform", "")
                if plat == "telegram" and "telegram_chat_id" not in kwargs:
                    kwargs["telegram_chat_id"] = platform_context.get("chat_id", "")
                kwargs["_telegram_client"] = self._telegram
                kwargs["_settings"] = self._settings

            tool = self._registry.get(func_name)

            # Check cache
            if tool.cache_ttl is not None:
                cache_key = f"{func_name}:{json.dumps(kwargs, sort_keys=True)}"
                cached = await self._cache.get(cache_key)
                if cached is not None:
                    return {
                        "tool_call_id": tc_id,
                        "role": "tool",
                        "content": json.dumps(cached, ensure_ascii=False),
                    }

            try:
                result = await tool.handler(**kwargs)
            except Exception as e:
                result = {"success": False, "error": str(e)}

            # Write cache
            if tool.cache_ttl is not None and result.get("success"):
                cache_key = f"{func_name}:{json.dumps(kwargs, sort_keys=True)}"
                await self._cache.set(cache_key, result, ttl=tool.cache_ttl)

            return {
                "tool_call_id": tc_id,
                "role": "tool",
                "content": json.dumps(result, ensure_ascii=False),
            }

        return await asyncio.gather(*[call_one(tc) for tc in tool_calls], return_exceptions=False)
