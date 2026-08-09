import logging
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from langchain.chat_models import init_chat_model

from backend.agent import BaseAgent
from backend.conversation import ConversationManager
from backend.tools import TOOLS, bind_conversation

load_dotenv()

logger = logging.getLogger(__name__)

app = FastAPI()

DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    async def listener(message: dict) -> None:
        await ws.send_json(message)

    conversation = ConversationManager(listener)
    bind_conversation(conversation)

    agent = BaseAgent(
        llm=init_chat_model(os.environ["MODEL"]),
        tools=TOOLS,
        conversation=conversation,
        agent_id=uuid.uuid4().hex,
    )

    try:
        while True:
            payload = await ws.receive_json()

            try:
                if payload.get("type") == "interrupt_response":
                    await agent.resume(payload["answer"])
                else:
                    text = (payload.get("text") or "").strip()
                    if not text:
                        continue
                    await agent.run(text)
            except Exception:
                logger.exception("Agent run failed")
                await ws.send_json({
                    "id": "error",
                    "type": "error",
                    "text": "The agent hit an error. Check the server logs.",
                })
            finally:
                await ws.send_json({"type": "idle"})

    except WebSocketDisconnect:
        pass


if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/")
    async def index():
        return FileResponse(DIST / "index.html")

else:

    @app.get("/")
    async def index():
        return PlainTextResponse(
            "The frontend is not built.\n\n"
            "Run `npm run dev` in frontend/ and open http://127.0.0.1:5173,\n"
            "or run `npm run build` and reload this page.\n"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.server:app", host="127.0.0.1", port=8001, reload=True)
