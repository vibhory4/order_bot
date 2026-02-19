import os
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

st.set_page_config(page_title="order_bot (MVP)", page_icon="🍰", layout="centered")

st.title("order_bot (MVP)")
st.caption("UI is minimal. Backend is the product.")

# ---------------------------
# Session state init
# ---------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {"role": "user"/"assistant", "content": str}

# ---------------------------
# Helper: call backend /chat
# ---------------------------
def call_chat(user_text: str):
    payload = {"message": user_text, "session_id": st.session_state.session_id}
    r = requests.post(f"{API_BASE}/chat", json=payload, timeout=60)
    r.raise_for_status()
    data = r.json()
    st.session_state.session_id = data["session_id"]
    return data["answer"]

# ---------------------------
# Render message history
# ---------------------------
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.write(m["content"])

# ---------------------------
# Chat input
# ---------------------------
user_text = st.chat_input("Type your message...")
if user_text:
    # show user message immediately
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.write(user_text)

    # get assistant reply
    try:
        answer = call_chat(user_text)
    except requests.RequestException as e:
        answer = f"Backend error: {e}"

    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.write(answer)

# ---------------------------
# Debug controls
# ---------------------------
with st.sidebar:
    st.subheader("Debug")
    st.write("API_BASE:", API_BASE)
    st.write("session_id:", st.session_state.session_id)

    if st.button("Reset chat"):
        st.session_state.session_id = None
        st.session_state.messages = []
        st.rerun()
