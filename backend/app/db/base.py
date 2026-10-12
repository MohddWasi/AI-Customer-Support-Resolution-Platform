from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped

class Base(DeclarativeBase):
    """base class for all sqlalchemy models"""

    pass

class TimestampMixin:
    """Adds creation and update timestamps to a model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now()
    )

    updated_at:Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        server_default=func.now(), 
        onupdate=func.now()
    )