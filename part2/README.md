# Part 2: Giving It Hands

Demo code for **Building AI Super Agents from Scratch, part 2**: shell and
Python access, web search, and human-in-the-loop with LangGraph interrupts.

```
backend/
  agent.py         BaseAgent: graph, checkpointer, run and resume
  conversation.py  ConversationManager: what the user sees
  tools.py         shell, run_python, web_search, ask_user
  server.py        FastAPI and the websocket
frontend/
  src/App.jsx      chat UI with the interrupt widget
workspace/         the directory the agent works in
```

## Run it

Backend:

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS and Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env            # then set MODEL and your API keys
python -m backend.server
```

Frontend, in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173. The dev server proxies `/ws` to the backend.

## Try it

`workspace/` is where the agent lives. Drop a few files in there, then ask for
something that needs all of it at once:

> Compare the numbers in my spreadsheets against the industry benchmark and
> save a short report in my workspace.

The agent explores the workspace, reads the files, searches the web for a
benchmark, asks you which benchmark and filename to use, then computes the
numbers and writes the report.
