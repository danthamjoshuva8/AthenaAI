from fastapi import FastAPI

app = FastAPI(
    title="AthenaAI API",
    version="1.0.0"
)

@app.get("/")
def home():
    return {
        "project": "AthenaAI",
        "status": "Running"
    }