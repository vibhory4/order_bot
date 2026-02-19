from fastapi import FastAPI

app = FastAPI(title="order_bot")

@app.get("/health")
def health():
    return {"status": "ok"}
