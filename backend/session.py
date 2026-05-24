from typing import Any, Dict, List

from prompt import SYSTEM_PROMPT

# In-memory store: session_id → list of messages.
# Simple and fast for an MVP, but restarting the server wipes all conversations.
# Replace with Redis or a database when persistence is needed.
SESSIONS: Dict[str, List[Dict[str, Any]]] = {}


def get_history(session_id: str) -> List[Dict[str, Any]]:
    if session_id not in SESSIONS:
        # Seed every new session with the system prompt as the first message.
        # OpenAI requires the system prompt to be part of the message list on every call.
        SESSIONS[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Returns a reference to the list, not a copy.
    # Callers can append directly and SESSIONS updates automatically.
    return SESSIONS[session_id]


def trim(history: List[Dict[str, Any]], keep_last: int = 14) -> None:
    # Keeps token cost flat by dropping old messages once history grows too long.
    # Always preserves history[0] (the system prompt) regardless of length.
    if len(history) > 1 + keep_last:
        # history[:] mutates the existing list in place instead of creating a new one.
        # A plain `history = [...]` would only update the local variable,
        # leaving SESSIONS pointing at the old, untrimmed list.
        history[:] = [history[0]] + history[-keep_last:]
