"""Context management: compaction and summarization."""

from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

KEEP_RECENT = 4
OFFLOAD_TRIGGER_CHARS = 4000

SUMMARY_PROMPT = """\
Summarize the conversation below into a dense digest for an agent that must
continue the work with no other memory of it.

Quote the user's requests and corrections directly. Keep every concrete
artifact: file paths, IDs, URLs, schemas, numbers, code snippets, decisions
already made, and approaches already ruled out. Record where the work stands
right now. No filler, no preamble.

{transcript}
"""


def estimate_tokens(messages: list[BaseMessage]) -> int:
    """Rough character-based estimate. Tool call arguments count too, since
    the model writes whole scripts in there."""
    total = 0

    for message in messages:
        total += len(str(message.content))

        for call in getattr(message, "tool_calls", None) or []:
            total += len(str(call.get("args", "")))

    return total // 4


def dedupe_repeated_commands(messages: list[BaseMessage]) -> list[BaseMessage]:
    commands = {
        call["id"]: call["args"].get("command")
        for message in messages
        if isinstance(message, AIMessage)
        for call in message.tool_calls
        if call["name"] == "shell"
    }

    seen: set[str] = set()

    for message in reversed(messages):
        if not isinstance(message, ToolMessage):
            continue

        command = commands.get(message.tool_call_id)
        if not command:
            continue

        if command in seen:
            message.content = f"[`{command}` ran again later, see the newer result below]"
        else:
            seen.add(command)

    return messages


def offload(content: str, name: str, cwd: Path) -> str:
    if len(content) < OFFLOAD_TRIGGER_CHARS:
        return content

    path = cwd / ".offload" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    head = "\n".join(content.splitlines()[:20])

    return (
        f"{head}\n\n"
        f"[Full output saved to {path.name}. Read it if you need more.]"
    )


def render(messages: list[BaseMessage]) -> str:
    lines = []

    for message in messages:
        role = type(message).__name__.replace("Message", "").lower()
        text = str(message.content).strip()

        if isinstance(message, AIMessage) and message.tool_calls:
            for call in message.tool_calls:
                text += f"\n[called {call['name']} {call['args']}]"

        if text:
            lines.append(f"<{role}>\n{text}\n</{role}>")

    return "\n\n".join(lines)


async def summarize_conversation(llm, messages: list[BaseMessage]) -> list[BaseMessage]:
    fold, keep = messages[:-KEEP_RECENT], messages[-KEEP_RECENT:]

    # never split a tool call from its result
    while keep and isinstance(keep[0], ToolMessage):
        fold, keep = messages[: len(fold) + 1], messages[len(fold) + 1 :]

    if not fold:
        return messages

    digest = await llm.ainvoke([
        HumanMessage(SUMMARY_PROMPT.format(transcript=render(fold)))
    ])

    return [
        HumanMessage(f"<summary>\n{digest.content}\n</summary>"),
        *keep,
    ]
