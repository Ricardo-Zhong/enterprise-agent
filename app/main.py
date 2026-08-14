from fastapi import FastAPI


app = FastAPI(title="Enterprise AI Agent", version="0.1.0")


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Return a lightweight service health signal."""
    return {"status": "ok", "service": "enterprise-agent"}
