import os
import platform
from datetime import datetime
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.types import Command, Overwrite

from backend.context import (
    dedupe_repeated_commands,
    estimate_tokens,
    summarize_conversation,
)
from backend.conversation import ConversationManager
from backend.skills import skill_index

# Deliberately small so the mechanics are visible in a short session.
# Real values are two orders of magnitude larger.
COMPACT_AT_TOKENS = 400
SUMMARIZE_AT_TOKENS = 1_000

SYSTEM_MESSAGE = f"""
You are a capable, careful assistant with access to a real machine.

Look before you act. Prefer one purposeful command over a series of exploratory
ones. Use run_python for calculations and for writing files. When a task is
done, say what you did in a sentence or two, not a report.

Answer with the numbers you actually computed, and never state a figure you
have not seen in a tool result.

<skills>
{skill_index()}
</skills>

Call learn_skill(name) to load the full instructions before you start work that
a skill covers. Follow the loaded instructions exactly.

<environment>
Platform: {platform.system()} {platform.release()}
Today: {datetime.now():%Y-%m-%d}
</environment>
"""


class BaseAgent:
    def __init__(
        self,
        llm: BaseChatModel,
        tools: list[BaseTool],
        conversation: ConversationManager,
        agent_id: str,
        system_message: str = SYSTEM_MESSAGE,
    ):
        self.tools = {tool.name: tool for tool in tools}
        self.llm = llm.bind_tools(list(self.tools.values()))
        self.summarizer = llm
        self.conversation = conversation
        self.system_message = system_message

        self._compacted_at = 0
        self._summarized_at = 0
        self._pending_usage = None

        self.checkpointer = InMemorySaver()
        self.config = {"configurable": {"thread_id": agent_id}}
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(MessagesState)

        graph.add_node("model", self._model_node)
        graph.add_node("tools", self._tools_node)

        graph.set_entry_point("model")

        graph.add_conditional_edges(
            "model",
            self._should_continue,
            {"continue": "tools", "end": END},
        )

        graph.add_edge("tools", "model")

        return graph.compile(checkpointer=self.checkpointer)

    async def _model_node(self, state: MessagesState) -> dict:
        messages = state["messages"]
        tokens = estimate_tokens(messages)

        # Only summarize once the stack has grown past the trigger *and* past
        # whatever the last summary left behind. Without the second condition,
        # a summary that lands above the trigger would summarize itself again
        # on every following turn.
        summarize_at = max(SUMMARIZE_AT_TOKENS, self._summarized_at + COMPACT_AT_TOKENS)

        if tokens > summarize_at:
            await self.conversation.add_event_message("summarizing")

            before = len(messages)
            messages = await summarize_conversation(self.summarizer, messages)
            self._summarized_at = estimate_tokens(messages)
            self._compacted_at = self._summarized_at

            await self.conversation.add_event_message(
                "summarized",
                {
                    "before": before,
                    "after": len(messages),
                    "tokens_before": tokens,
                    "tokens_after": self._summarized_at,
                },
            )

        elif tokens - self._compacted_at > COMPACT_AT_TOKENS:
            messages = dedupe_repeated_commands(messages)
            self._compacted_at = estimate_tokens(messages)

        reply = await self.llm.ainvoke([
            SystemMessage(self.system_message), *messages
        ])

        if reply.content:
            await self.conversation.add_ai_message(_text_of(reply))

        if reply.tool_calls:
            # the tools run in the next node, so hold the usage until after
            # their messages land, otherwise it renders above them
            self._pending_usage = reply.usage_metadata
        else:
            await self.conversation.add_usage_message(reply.usage_metadata)

        return {"messages": Overwrite(value=[*messages, reply])}

    async def _tools_node(self, state: MessagesState) -> dict:
        last = state["messages"][-1]

        results = []
        for call in last.tool_calls:
            tool = self.tools[call["name"]]
            result = await tool.ainvoke(call["args"])

            results.append(
                ToolMessage(content=str(result), tool_call_id=call["id"])
            )

        await self.conversation.add_usage_message(self._pending_usage)
        self._pending_usage = None

        return {"messages": results}

    def _should_continue(self, state: MessagesState) -> Literal["continue", "end"]:
        last = state["messages"][-1]
        return "continue" if getattr(last, "tool_calls", None) else "end"

    async def run(self, message: str):
        await self.conversation.add_human_message(message)

        result = await self.graph.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            config=self.config,
        )

        return await self._settle(result)

    async def resume(self, answer):
        result = await self.graph.ainvoke(
            Command(resume=answer),
            config=self.config,
        )

        return await self._settle(result)

    async def _settle(self, result: dict):
        interrupts = result.get("__interrupt__")

        if interrupts:
            request = interrupts[0].value
            await self.conversation.add_interrupt_message(request)
            return request

        return result["messages"][-1]


def _text_of(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content.strip()

    return "".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    ).strip()


