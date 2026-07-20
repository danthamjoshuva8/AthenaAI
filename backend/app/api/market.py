from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.database.session import get_db

from app.services.market_service import MarketService
from app.schemas.market_data import HistoryLoadRequest
from datetime import datetime
from app.models.sector import Sector

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

@router.delete("/clear")
def clear_market_data(
    db: Session = Depends(get_db)
):

    return service.clear_market_data(
        db
    )

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

@router.post(
    "/history/nifty50"
)
def load_nifty50_history(
    years: int = 7,
    db: Session = Depends(get_db)
):

    service = MarketService()

    return service.load_nifty_index_history(
        db,
        years
    )

@router.get("/history/nifty50/test")
def test_nifty(
    date: str,
    db: Session = Depends(get_db)
):

    service = MarketService()

    df = service.get_nifty_history(
        db,
        datetime.strptime(
            date,
            "%Y-%m-%d"
        ).date()
    )

    df = service.prepare_nifty_context(df)

    return {

        "rows": len(df),

        "last_date": str(df.iloc[-1]["Date"]),

        "last_close": float(df.iloc[-1]["Close"]),

        "last_ma150": float(df.iloc[-1]["MA150"])

    }

@router.post("/history/sector/{sector}")
def load_sector_history(
    sector: Sector,
    years: int = 7,
    db: Session = Depends(get_db)
):

    result = MarketService().load_sector_history(
        db=db,
        sector=sector,
        years=years
    )

    return result

@router.post("/stock-master")
def load_stock_master(
    db: Session = Depends(get_db)
):

    return MarketService().load_stock_master(
        db=db
    )