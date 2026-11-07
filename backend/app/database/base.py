
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Shared declarative base for all SQLAlchemy ORM models.

    All database model classes should inherit from this class.
    SQLAlchemy uses this base to register model metadata
    and manage table definitions.
    """
    pass
