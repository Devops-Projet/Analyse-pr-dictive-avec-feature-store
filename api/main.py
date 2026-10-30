from fastapi import FastAPI

app = FastAPI(title="Feature store bancaire")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
