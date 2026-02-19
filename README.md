# order_bot (MVP)

Dockerized FastAPI backend + Streamlit UI. Collects cake order leads for Bakeology.

## Run locally
1. Copy env example:
   cp .env.example .env

2. Put your OpenAI key in `.env`

3. Start:
   docker compose up --build

Backend: http://localhost:8000/docs  
UI: http://localhost:8501

## Env
- OPENAI_API_KEY
- OPENAI_MODEL (default: gpt-4o-mini)
