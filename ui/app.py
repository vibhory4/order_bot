import os
import requests
import streamlit as st

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

st.title("order_bot (MVP)")
st.caption("UI is minimal. Backend is the product.")

if st.button("Check backend /health"):
    r = requests.get(f"{API_BASE}/health", timeout=30)
    st.json(r.json())
