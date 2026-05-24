# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the project

```bash
cp .env.example .env   # once — then add OPENAI_API_KEY
docker compose up --build
```

After any change to `.py` files, restart with:
```bash
docker compose down && docker compose build --no-cache && docker compose up
```

Use `--no-cache` when adding new files — Docker caches image layers aggressively and won't pick up new files otherwise.

- UI: http://localhost:8501
- Backend API docs: http://localhost:8000/docs
- Backend health: http://localhost:8000/health

## Architecture

Two Docker services defined in `docker-compose.yml`:

**backend/** — FastAPI app, the core product
- `main.py` — FastAPI app instance and all route definitions (`/`, `/health`, `/chat`)
- `config.py` — reads `OPENAI_API_KEY` / `OPENAI_MODEL` from env, initialises the OpenAI client
- `models.py` — Pydantic request/response schemas (`ChatIn`, `ChatOut`)
- `prompt.py` — `SYSTEM_PROMPT` constant defining the bot's persona, P0 collection rules, privacy and security guardrails
- `session.py` — in-memory `SESSIONS` dict keyed by `session_id`; `get_history()` and `trim()` manage per-session message lists

**ui/** — Streamlit frontend, intentionally minimal
- `app.py` — page layout and chat rendering only
- `api.py` — `API_BASE` env var and `call_chat()` which POSTs to the backend

## Key design decisions

**Session memory is in-process.** `SESSIONS` is a plain Python dict in the backend process. All history is lost on container restart. There is no database.

**History trimming.** `trim()` in `session.py` keeps the system prompt plus the last 14 messages to control token cost. It is called once per request, after the assistant reply is appended.

**OpenAI client initialisation.** The client is created at import time in `config.py`. If `OPENAI_API_KEY` is absent the client is `None` and `/chat` returns HTTP 500. The check happens before any session work in `main.py`.

**Docker COPY strategy.** Both Dockerfiles use `COPY *.py .` so all Python modules in the service directory are included in the image.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | — | Required. Passed to backend container only. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model used for all chat completions. |
| `API_BASE` | `http://localhost:8000` | Set to `http://backend:8000` inside Docker by compose. |
