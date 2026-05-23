import requests
import streamlit as st

from api import API_BASE, call_chat

st.set_page_config(page_title="order_bot (MVP)", page_icon="🍰", layout="centered")

st.title("order_bot (MVP)")
st.caption("UI is minimal. Backend is the product.")

if "session_id" not in st.session_state:
    st.session_state.session_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.write(m["content"])

user_text = st.chat_input("Type your message...")
if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.write(user_text)

    try:
        answer = call_chat(user_text)
    except requests.RequestException as e:
        answer = f"Backend error: {e}"

    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant"):
        st.write(answer)

with st.sidebar:
    st.subheader("Debug")
    st.write("API_BASE:", API_BASE)
    st.write("session_id:", st.session_state.session_id)

    if st.button("Reset chat"):
        st.session_state.session_id = None
        st.session_state.messages = []
        st.rerun()
