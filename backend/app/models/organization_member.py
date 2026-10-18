from sqlalchemy import ForeignKey, Uuid, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin
import enum
import uuid


class OrganizationRole(str, enum.Enum):
    CUSTOMER = "customer"
    SUPPORT_AGENT = "support_agent"
    ADMIN = "admin"

class OrganizationMember(Base, TimestampMixin):
    """OrganizationMember model."""
    __tablename__ = "organization_members"

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_organization_members_organization_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid7)
    organization_id: Mapped[uuid.UUID] = mapped_column(Uuid,ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[OrganizationRole] = mapped_column(Enum(OrganizationRole, 
          name="organization_role",
          native_enum=False,        # stored as VARCHAR, not a Postgres ENUM type
          create_constraint=True,   # adds a CHECK constraint (off by default)
          length=50,
          values_callable=lambda e: [m.value for m in e],  # store "admin", not "ADMIN"
      ), nullable=False)
