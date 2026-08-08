import uuid
from typing import Awaitable, Callable


class ConversationManager:
    def __init__(self, listener: Callable[[dict], Awaitable[None]]):
        self._listener = listener
        self._messages: list[dict] = []

    @property
    def messages(self) -> list[dict]:
        return list(self._messages)

    async def _add_message(self, message_type: str, text: str) -> None:
        message = {
            "id": uuid.uuid4().hex,
            "type": message_type,
            "text": text,
        }
        self._messages.append(message)
        await self._listener(message)

    async def add_human_message(self, message: str) -> None:
        if message:
            await self._add_message("human", message)

    async def add_ai_message(self, message: str) -> None:
        if message:
            await self._add_message("text", message)
