from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.database import router as database_router
from app.api.market import router as market_router
from app.api.strategy import router as strategy_router

app = FastAPI(
    title="AthenaAI",
    version="1.0.0"
)

app.include_router(health_router)
app.include_router(database_router)
app.include_router(market_router)
app.include_router(strategy_router)


@app.get("/")
def home():

    return {
        "project": "AthenaAI",
        "status": "Running"
    }