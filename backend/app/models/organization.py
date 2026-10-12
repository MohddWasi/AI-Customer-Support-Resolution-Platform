import uuid

from sqlalchemy import String,Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin

class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id:Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name:Mapped[str] = mapped_column(String(150), nullable=False, unique=True)