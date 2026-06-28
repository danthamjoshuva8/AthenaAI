from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.strategy_service import StrategyService

router = APIRouter(
    prefix="/strategy",
    tags=["Strategy"]
)

service = StrategyService()


@router.get("/load/{symbol}")
def load_market_data(
    symbol: str,
    db: Session = Depends(get_db)
):

    data = service.load_data(
        db,
        symbol
    )

    return {

        "rows": len(data),

        "symbol": symbol

    }

@router.get("/ma/{symbol}")
def moving_average(
    symbol: str,
    db: Session = Depends(get_db)
):

    df = service.calculate_ma(
        db,
        symbol
    )

    return df.tail(20).to_dict(
        orient="records"
    )

@router.get("/signals/{symbol}")
def strategy_signals(
    symbol: str,
    db: Session = Depends(get_db)
):

    return service.generate_signals(
        db,
        symbol
    )

@router.get("/latest/{symbol}")
def latest_signal(
    symbol: str,
    db: Session = Depends(get_db)
):

    return service.latest_signal(
        db,
        symbol
    )

@router.get("/buy/{symbol}")
def buy_signals(
    symbol: str,
    db: Session = Depends(get_db)
):

    return service.buy_signals(
        db,
        symbol
    )

@router.get("/sell/{symbol}")
def sell_signals(
    symbol: str,
    db: Session = Depends(get_db)
):

    return service.sell_signals(
        db,
        symbol
    )