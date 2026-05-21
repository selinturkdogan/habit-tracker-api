from fastapi import FastAPI

app = FastAPI(
    title="Habit Tracker API",
    description="Backend for the Habit Tracker app — SFWE477 final project.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
