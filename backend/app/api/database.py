from fastapi import APIRouter
from sqlalchemy import text

from app.database.session import engine
from app.database.base import Base

import app.database.models

router = APIRouter(
    prefix="/database",
    tags=["Database"]
)


@router.get("/status")
def database_status():

    try:

        with engine.connect() as connection:

            connection.execute(text("SELECT 1"))

        return {
            "database": "Connected"
        }

    except Exception as ex:

        return {
            "database": "Disconnected",
            "error": str(ex)
        }


@router.post("/init")
def initialize_database():

    Base.metadata.create_all(bind=engine)

    return {
        "message": "Database tables created successfully"
    }