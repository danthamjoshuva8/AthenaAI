from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.backtest_service import BacktestService
from app.utils.nifty200 import get_nifty200_symbols

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

@router.get("/portfolio")
def portfolio_metrics(
    db: Session = Depends(get_db)
):

    symbols = get_nifty200_symbols()

    service = BacktestService()

    return service.portfolio_metrics(
        db,
        symbols
    )

@router.get("/portfolio/timeline")
def portfolio_timeline(
    db: Session = Depends(get_db)
):

    symbols = get_nifty200_symbols()

    return service.execute_portfolio(

        db,

        symbols

    )

@router.get("/portfolio/summary")
def portfolio_summary(
    db: Session = Depends(get_db)
):

    symbols = get_nifty200_symbols()

    return service.portfolio_summary(
        db,
        symbols
    )

@router.get("/portfolio/statistics")
def portfolio_statistics(
    db: Session = Depends(get_db)
):

    symbols = get_nifty200_symbols()

    return service.portfolio_statistics(
        db,
        symbols
    )

@router.get("/portfolio/trade-analytics")
def trade_analytics(
    db: Session = Depends(get_db)
):

    symbols = get_nifty200_symbols()

    return service.trade_analytics(
        db,
        symbols
    )

@router.get("/portfolio/risk-analytics")
def risk_analytics(
    db: Session = Depends(get_db)
):

    symbols = get_nifty200_symbols()

    return service.risk_analytics(
        db,
        symbols
    )

@router.get("/portfolio/holding-analytics")
def holding_analytics(
    db: Session = Depends(get_db)
):

    symbols = get_nifty200_symbols()

    return service.holding_analytics(
        db,
        symbols
    )

@router.get("/portfolio/monthly-analytics")
def monthly_analytics(
    db: Session = Depends(get_db)
):

    symbols = get_nifty200_symbols()

    return service.monthly_analytics(
        db,
        symbols
    )

@router.get("/portfolio/yearly-analytics")
def yearly_analytics(
    db: Session = Depends(get_db)
):

    symbols = get_nifty200_symbols()

    return service.yearly_analytics(
        db,
        symbols
    )

@router.get("/portfolio/market-analytics")
def market_analytics(
    db: Session = Depends(get_db)
):

    symbols = get_nifty200_symbols()

    return service.market_analytics(
        db,
        symbols
    )

@router.get("/portfolio/sector-analytics")
def sector_analytics(
    db: Session = Depends(get_db)
):

    symbols = get_nifty200_symbols()

    return service.sector_analytics(

        db,

        symbols

    )

@router.get("/portfolio/skipped-trade-analytics")
def skipped_trade_analytics(
    db: Session = Depends(get_db)
):

    symbols = get_nifty200_symbols()

    return service.skipped_trade_analytics(

        db,

        symbols

    )

@router.get("/portfolio/capital-utilization")
def capital_utilization(
    db: Session = Depends(get_db)
):

    symbols = get_nifty200_symbols()

    return service.capital_utilization_analytics(
        db,
        symbols
    )

@router.get("/portfolio/overlap-analytics")
def overlap_analytics(
    db: Session = Depends(get_db)
):

    symbols = get_nifty200_symbols()

    return service.overlap_analytics(
        db,
        symbols
    )

@router.get("/portfolio/optimize")
def optimize(
    db: Session = Depends(get_db)
):

    symbols = get_nifty200_symbols()

    return service.optimize_strategy(
        db,
        symbols
    )