from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.backtest_service import BacktestService

router = APIRouter(
    prefix="/backtest",
    tags=["Backtesting"]
)

service = BacktestService()


@router.get("/signals/{symbol}")
def load_signals(
    symbol: str,
    db: Session = Depends(get_db)
):

    signals = service.load_signals(
        db,
        symbol
    )

    return {

        "symbol": symbol,

        "total_signals": len(signals)

    }

@router.get("/positions/{symbol}")
def simulate_positions(
    symbol: str,
    db: Session = Depends(get_db)
):

    return service.simulate_positions(
        db,
        symbol
    )

@router.get("/trades/{symbol}")
def execute_trades(
    symbol: str,
    db: Session = Depends(get_db)
):

    return service.execute_trades(
        db,
        symbol
    )

@router.get("/metrics/{symbol}")
def performance_metrics(
    symbol: str,
    db: Session = Depends(get_db)
):

    return service.performance_metrics(
        db,
        symbol
    )

@router.get("/equity/{symbol}")
def equity_curve(
    symbol: str,
    db: Session = Depends(get_db)
):

    return service.equity_curve(
        db,
        symbol
    )

@router.get("/drawdown/{symbol}")
def drawdown_metrics(
    symbol: str,
    db: Session = Depends(get_db)
):

    return service.drawdown_metrics(
        db,
        symbol
    )