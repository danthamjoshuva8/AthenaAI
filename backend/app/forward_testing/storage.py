
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)

from app.database.base import Base


class PaperOrder(Base):
    """Stores every forward-testing paper order."""

    __tablename__ = "forward_testing_orders"

    id = Column(Integer, primary_key=True, index=True)

    symbol = Column(String(30), nullable=False, index=True)
    order_type = Column(String(10), nullable=False, default="BUY")
    status = Column(String(20), nullable=False, index=True)

    execution_date = Column(Date, nullable=False, index=True)

    quantity = Column(Integer)
    signal_entry_price = Column(Float)
    execution_price = Column(Float)
    stop_loss = Column(Float)

    gross_value = Column(Float)
    brokerage = Column(Float)
    total_cost = Column(Float)
    slippage_bps = Column(Float)
    risk_amount = Column(Float)

    reason = Column(Text)

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    run_id = Column(
        Integer,
        ForeignKey("forward_testing_runs.id"),
        nullable=True,
        index=True,
    )


class PaperPosition(Base):
    """Stores the current and historical state of paper positions."""

    __tablename__ = "forward_testing_positions"

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(
        Integer,
        ForeignKey("forward_testing_orders.id"),
        nullable=True,
        index=True,
    )

    symbol = Column(String(30), nullable=False, index=True)

    entry_date = Column(Date, nullable=False)
    entry_price = Column(Float, nullable=False)

    quantity = Column(Integer, nullable=False)
    remaining_quantity = Column(Integer, nullable=False)

    stop_loss = Column(Float, nullable=False)
    initial_stop_loss = Column(Float, nullable=False)
    initial_risk = Column(Float, nullable=False)

    target_2r = Column(Float)
    target_3r = Column(Float)

    partial_exit_2r = Column(Boolean, default=False)
    partial_exit_3r = Column(Boolean, default=False)
    trail_active = Column(Boolean, default=False)

    realized_pnl = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)

    status = Column(String(20), nullable=False, index=True)
    exit_strategy = Column(String(50), nullable=False)

    last_updated_date = Column(Date)
    exit_date = Column(Date)
    final_exit_reason = Column(String(100))

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class PaperPositionEvent(Base):
    """Stores individual position-management and exit events."""

    __tablename__ = "forward_testing_position_events"

    id = Column(Integer, primary_key=True, index=True)

    position_id = Column(
        Integer,
        ForeignKey("forward_testing_positions.id"),
        nullable=False,
        index=True,
    )

    event_date = Column(Date, nullable=False, index=True)

    action = Column(String(30), nullable=False)
    sell_quantity = Column(Integer, default=0)
    remaining_quantity = Column(Integer)

    exit_price = Column(Float)
    exit_reason = Column(String(100))

    realized_pnl = Column(Float, default=0.0)
    cumulative_realized_pnl = Column(Float, default=0.0)

    details = Column(JSON)

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

class ForwardTestingRun(Base):
    __tablename__ = "forward_testing_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_key = Column(String(100), unique=True, nullable=False, index=True)

    signal_date = Column(Date, nullable=False)
    execution_date = Column(Date, nullable=False)

    status = Column(String(20), nullable=False, default="RUNNING")
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
