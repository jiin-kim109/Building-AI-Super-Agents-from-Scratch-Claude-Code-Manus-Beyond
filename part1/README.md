# Part 1: The Loop

The ReAct loop on LangGraph, agent messages vs conversation messages, and a
websocket chat UI. The agent has one tool, `execute_python`.

```
backend/
  agent.py         BaseAgent: the graph, the loop, the run entry point
  conversation.py  ConversationManager: the messages the user sees
  tools.py         execute_python
  server.py        FastAPI and the websocket
frontend/
  src/App.jsx      the chat UI
```

## Run it

Backend:

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS and Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env            # then set MODEL and your API key
python -m backend.server
```

Frontend, in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173. The dev server proxies `/ws` to the backend.

To serve everything from FastAPI instead, run `npm run build` in `frontend/`
and open http://127.0.0.1:8000.

## Notes

`execute_python` runs code in a subprocess with a timeout. That is enough to
demonstrate the loop and nowhere near enough to run untrusted code. Part 2
replaces it with a sandboxed capability.

Agent messages live in a Python list on `BaseAgent`, so the agent remembers
the current conversation and forgets it on restart.
