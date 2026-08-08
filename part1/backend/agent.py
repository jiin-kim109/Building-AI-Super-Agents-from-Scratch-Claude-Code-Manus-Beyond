from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, MessagesState, StateGraph

from backend.conversation import ConversationManager


class BaseAgent:
    def __init__(
        self,
        llm: BaseChatModel,
        tools: list[BaseTool],
        conversation: ConversationManager,
    ):
        self.tools = {tool.name: tool for tool in tools}
        self.llm = llm.bind_tools(list(self.tools.values()))
        self.conversation = conversation
        self.messages: list[BaseMessage] = []
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

        return graph.compile()

    async def _model_node(self, state: MessagesState) -> dict:
        reply = await self.llm.ainvoke(state["messages"])

        if reply.content:
            await self.conversation.add_ai_message(reply.content)

        return {"messages": [reply]}

    async def _tools_node(self, state: MessagesState) -> dict:
        last = state["messages"][-1]

        results = []
        for call in last.tool_calls:
            tool = self.tools[call["name"]]
            result = await tool.ainvoke(call["args"])

            results.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=call["id"],
                )
            )

        return {"messages": results}

    def _should_continue(self, state: MessagesState) -> Literal["continue", "end"]:
        last = state["messages"][-1]
        return "continue" if getattr(last, "tool_calls", None) else "end"

    async def run(self, message: str) -> BaseMessage:
        await self.conversation.add_human_message(message)
        self.messages.append(HumanMessage(content=message))

        result = await self.graph.ainvoke({"messages": self.messages})
        self.messages = result["messages"]

        return result["messages"][-1]
