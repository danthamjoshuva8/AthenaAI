
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.historical_signal_replay_service import (
    HistoricalSignalReplayService
)


router = APIRouter()

service = HistoricalSignalReplayService()


class HistoricalScanRequest(BaseModel):

    scan_date: date


@router.post("/forward-testing/historical-scan")
def historical_signal_scan(
    request: HistoricalScanRequest,
    db: Session = Depends(get_db)
):

    try:

        result = service.scan(
            db=db,
            scan_date=request.scan_date
        )

        return jsonable_encoder(result)

    except ValueError as ex:

        raise HTTPException(
            status_code=400,
            detail=str(ex)
        )

    except Exception:

        raise HTTPException(
            status_code=500,
            detail="Historical signal replay failed."
        )
