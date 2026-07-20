from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.database.session import get_db

from app.services.trade_selection_service import (
    TradeSelectionService
)

router = APIRouter()

service = TradeSelectionService()


@router.get("/scan")

def scan_market(

    db: Session = Depends(get_db)

):

    return service.scan_market(db)