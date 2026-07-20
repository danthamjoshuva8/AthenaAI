from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.database import router as database_router
from app.api.market import router as market_router
from app.api.strategy import router as strategy_router
from app.api.backtest import router as backtest_router
from app.api import trade_selection
from app.api import allocation

app = FastAPI(
    title="AthenaAI",
    version="1.0.0"
)

app.include_router(health_router)
app.include_router(database_router)
app.include_router(market_router)
app.include_router(strategy_router)
app.include_router(backtest_router)
app.include_router(

    trade_selection.router,

    prefix="/trade-selection",

    tags=["Trade Selection"]

)
app.include_router(
    allocation.router,
    prefix="/allocation",
    tags=["Allocation"]
)


@app.get("/")
def home():

    return {
        "project": "AthenaAI",
        "status": "Running"
    }