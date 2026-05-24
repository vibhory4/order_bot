import os

import requests
import streamlit as st

API_BASE = os.getenv("API_BASE", "http://localhost:8000")


def call_chat(user_text: str) -> str:
    payload = {"message": user_text, "session_id": st.session_state.session_id}
    r = requests.post(f"{API_BASE}/chat", json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    st.session_state.session_id = data["session_id"]
    return data["answer"]
