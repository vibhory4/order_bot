import uuid

from fastapi import FastAPI, HTTPException

from config import client, MODEL
from models import ChatIn, ChatOut
from session import get_history, trim

app = FastAPI(title="order_bot")


@app.get("/")
def root():
    return {"message": "order_bot backend running. Visit /docs or /health."}


# /health exists for infrastructure — Docker and monitoring tools poll this
# to know if the server process is alive. Keep it cheap (no DB or API calls).
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatOut)
def chat(payload: ChatIn):
    # Fail early with a clear message instead of letting the OpenAI call fail
    # with a cryptic auth error later.
    if client is None:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set in container environment")

    # Generate a new session ID only when the client sends none (first message).
    # uuid4 is random — collision probability is negligible at this scale.
    session_id = payload.session_id or str(uuid.uuid4())
    history = get_history(session_id)

    # Append before calling OpenAI so the latest message is included in the input.
    history.append({"role": "user", "content": payload.message})

    # Send the full conversation history on every call.
    # OpenAI has no memory — context must be re-supplied each time.
    resp = client.responses.create(
        model=MODEL,
        input=history,
        truncation="auto",  # fallback if history somehow exceeds the model's context window
    )

    answer = resp.output_text

    # Store the reply before trimming so it is never accidentally dropped.
    history.append({"role": "assistant", "content": answer})
    trim(history)

    return ChatOut(session_id=session_id, answer=answer)
