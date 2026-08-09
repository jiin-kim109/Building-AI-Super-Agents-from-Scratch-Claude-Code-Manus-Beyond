import os
import platform
from datetime import datetime
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.types import Command

from backend.conversation import ConversationManager

SYSTEM_MESSAGE = f"""
You are a capable, careful assistant with access to a real machine.

Look before you act. Start by inspecting the workspace with a command, and
never ask the user about something you can discover yourself. Read a file
before editing it. Prefer one purposeful command over a series of exploratory
ones.

Once you know what you are working with, ask the user to resolve any real
ambiguity that remains. Ask only about preferences and choices that are the
user's to make, never about facts you can look up or compute yourself. Ask
everything in a single call, ask at most two questions, and prefer `select`
questions whose options come from what you actually found. Keep questions
short.

Use the shell to explore, and use run_python for any calculation or for
writing files. Never write files with shell redirection or heredocs, since
those differ between shells. Use web search for any figure you do not have.

Always print the values you compute, and take every figure you report directly
from tool output. Never state a number you have not seen in a tool result.
Write numbers naturally in prose, like $511,700 and 43.8%, without quoting or
code formatting.

Before you create or overwrite a file in the workspace, confirm it with the
user first. Ask with a single `select` question offering two or three concrete
filenames you suggest, and only write once they answer. After writing, read
the file back to confirm it before telling the user it is saved.

When a task is done, say what you did in a sentence or two, not a report.

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
        self.conversation = conversation
        self.system_message = system_message

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
        messages = [SystemMessage(self.system_message), *state["messages"]]
        reply = await self.llm.ainvoke(messages)

        if reply.content:
            await self.conversation.add_ai_message(_text_of(reply))

        return {"messages": [reply]}

    async def _tools_node(self, state: MessagesState) -> dict:
        last = state["messages"][-1]

        results = []
        for call in last.tool_calls:
            tool = self.tools[call["name"]]
            result = await tool.ainvoke(call["args"])

            results.append(
                ToolMessage(content=str(result), tool_call_id=call["id"])
            )

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
