# Part 3: Managing Context

Demo code for **Building AI Super Agents from Scratch, part 3**: prompt
caching, compaction and summarization, and progressive disclosure through
skills.

```
backend/
  agent.py         BaseAgent, with compaction and summarization in the model node
  context.py       dedupe_repeated_commands, offload, summarize_conversation
  skills.py        the skill index and loader
  tools.py         shell, run_python, learn_skill, web_search, ask_user
  conversation.py  what the user sees, including skill and usage messages
  server.py        FastAPI and the websocket
frontend/
  src/App.jsx      chat UI with skill, usage, and summarization indicators
skills/
  warehouse/       domain knowledge the model cannot have
  billing_api/
  deploy/
```

## Run it

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS and Linux: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env            # then set MODEL and your API keys
python seed_warehouse.py        # creates workspace/warehouse.db
python -m backend.server
```

Frontend, in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173.

## Try it

Ask something that needs the warehouse skill, then keep going:

> How many active users did we have in the last 28 days?

> What was our total revenue, and how does it split by plan?

> Break that down by month for the last 6 months.

> Give me a one-line summary of everything you found.

The agent loads the `warehouse` skill on the first question, and the token
counts under each turn show the cached prefix growing. A few turns in, the
conversation crosses the summarization threshold and folds itself down.

## Thresholds

`COMPACT_AT_TOKENS` and `SUMMARIZE_AT_TOKENS` in `backend/agent.py` are set
deliberately low so the mechanics are visible in a short session. Real values
are two orders of magnitude larger.
