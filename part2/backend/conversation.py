import uuid
from typing import Awaitable, Callable


class ConversationManager:
    def __init__(self, listener: Callable[[dict], Awaitable[None]]):
        self._listener = listener
        self._messages: list[dict] = []

    @property
    def messages(self) -> list[dict]:
        return list(self._messages)

    async def _add_message(self, message: dict) -> None:
        message = {"id": uuid.uuid4().hex, **message}
        self._messages.append(message)
        await self._listener(message)

    async def add_human_message(self, message: str) -> None:
        if message:
            await self._add_message({"type": "human", "text": message})

    async def add_ai_message(self, message: str) -> None:
        if message:
            await self._add_message({"type": "text", "text": message})

    async def add_tool_message(self, name: str, description: str) -> None:
        last = self._messages[-1] if self._messages else None
        if last and last.get("type") == "tool" and last.get("description") == description:
            return

        await self._add_message({
            "type": "tool",
            "name": name,
            "description": description,
        })

    async def add_interrupt_message(self, request: dict) -> None:
        await self._add_message({"type": "interrupt", "request": request})
