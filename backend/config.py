import os
from openai import OpenAI

# Read from environment so the same code works in dev, staging, and prod
# without changing any files — just change the env vars.
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# client is None when the key is missing instead of crashing here,
# so the server still starts and /health still responds.
# The actual error is raised inside /chat where the key is first needed.
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
