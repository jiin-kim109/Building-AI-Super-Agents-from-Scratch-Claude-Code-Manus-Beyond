import asyncio
import os
import sys
import uuid
from pathlib import Path
from typing import Literal

from langchain_core.tools import tool
from langgraph.types import interrupt
from pydantic import BaseModel
from tavily import AsyncTavilyClient

from backend.context import offload
from backend.skills import load_skill

CWD = Path(__file__).resolve().parent.parent / "workspace"
CWD.mkdir(parents=True, exist_ok=True)

_conversation = None


def bind_conversation(conversation) -> None:
    global _conversation
    _conversation = conversation


async def _notify(name: str, description: str) -> None:
    if _conversation is not None:
        await _conversation.add_tool_message(name, description)


async def _run(command: str, name: str) -> str:
    proc = await asyncio.create_subprocess_shell(
        command,
        cwd=CWD,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    output, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
    text = output.decode(errors="replace")

    return f"exit={proc.returncode}\n{offload(text, name, CWD)}"


@tool
async def shell(command: str, description: str) -> str:
    """Run a shell command and return its output.

    Args:
        command: the command to run
        description: a short present-tense note shown to the user,
            for example "Listing the project files"
    """
    await _notify("shell", description)

    return await _run(command, f"shell_{uuid.uuid4().hex[:8]}.txt")


@tool
async def run_python(code: str, description: str) -> str:
    """Write a Python script to the workspace and run it.

    Use this for calculations, data processing, and writing files.

    Args:
        code: the Python source to run
        description: a short present-tense note shown to the user
    """
    await _notify("run_python", description)

    path = CWD / ".scripts" / f"{uuid.uuid4().hex[:8]}.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(code, encoding="utf-8")

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(path),
        cwd=CWD,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    output, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
    text = output.decode(errors="replace")

    return f"exit={proc.returncode}\n{offload(text, path.stem + '.txt', CWD)}"


@tool
async def learn_skill(name: str) -> str:
    """Load the full instructions for a skill.

    Call this before doing the kind of work the skill describes.

    Args:
        name: the skill name from the index in the system message
    """
    if _conversation is not None:
        await _conversation.add_skill_message(name)

    return load_skill(name)


@tool
async def web_search(query: str, max_results: int = 5) -> str:
    """Search the web and return relevant excerpts with their sources.

    Args:
        query: what to search for, phrased as a search query
        max_results: how many results to return
    """
    await _notify("web_search", f"Searching the web for {query}")

    tavily = AsyncTavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    response = await tavily.search(query, max_results=max_results)

    return "\n\n".join(
        f"{r['title']}\n{r['url']}\n{r['content']}" for r in response["results"]
    )


class Question(BaseModel):
    id: str
    type: Literal["text", "select"]
    question: str
    options: list[str] = []


@tool
async def ask_user(questions: list[Question]) -> str:
    """Ask the user one or more clarification questions.

    Ask when the request is ambiguous and guessing would waste real work.
    """
    answers = interrupt({
        "type": "ask_user",
        "questions": [q.model_dump() for q in questions],
    })

    return "\n".join(f"Q: {a['question']}\nA: {a['answer']}" for a in answers)


TOOLS = [shell, run_python, learn_skill, web_search, ask_user]
