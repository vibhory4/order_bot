from typing import Optional
from pydantic import BaseModel, Field


# ChatIn defines what the caller MUST send in the POST body.
# Pydantic validates this automatically — bad input returns a 422 error
# before our code even runs.
class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)  # cap at 2000 chars to control OpenAI token cost
    session_id: Optional[str] = None  # None on first message; backend generates a new session ID


# ChatOut defines what we ALWAYS return — both fields are always present.
# session_id is echoed back so the UI can persist it for the next request.
class ChatOut(BaseModel):
    session_id: str
    answer: str
