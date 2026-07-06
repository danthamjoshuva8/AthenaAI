from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.database.session import get_db

from app.services.market_service import MarketService
from app.schemas.market_data import HistoryLoadRequest

router = APIRouter(
    prefix="/market",
    tags=["Market Data"]
)

service = MarketService()


@router.get("/ping")
def ping():

    return service.ping()


@router.get("/download/{symbol}")
def download(symbol: str):

    df = service.download_history(symbol)

    return {
        "symbol": symbol,
        "rows": len(df),
        "columns": list(df.columns)
    }

@router.post("/save/{symbol}")
def save_market_data(
    symbol: str,
    db: Session = Depends(get_db)
):

    rows = service.save_history(
        db,
        symbol
    )

    return {

        "message": "Data Saved",

        "rows": rows
    }

@router.get("/all")
def get_all_market_data(
    db: Session = Depends(get_db)
):

    data = service.get_all_data(db)

    return data

@router.get("/stats")
def market_statistics(
    db: Session = Depends(get_db)
):

    return service.statistics(db)

@router.delete("/{symbol}")
def delete_symbol(
    symbol: str,
    db: Session = Depends(get_db)
):

    deleted = service.delete_symbol(
        db,
        symbol
    )

    return {

        "deleted_rows": deleted

    }

@router.get("/{symbol}")
def get_symbol_market_data(
    symbol: str,
    db: Session = Depends(get_db)
):

    data = service.get_symbol_data(
        db,
        symbol
    )

    return data

@router.post("/load-history")
def load_history(
    request: HistoryLoadRequest,
    db: Session = Depends(get_db)
):

    return service.load_history(
        db,
        request.years
    )