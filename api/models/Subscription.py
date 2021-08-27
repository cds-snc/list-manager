import datetime
import uuid

from sqlalchemy import Boolean, DateTime, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from models import Base
from models.List import List


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String)
    phone = Column(String)
    confirmed = Column(Boolean, unique=False, default=False)
    created_at = Column(
        DateTime,
        index=False,
        unique=False,
        nullable=False,
        default=datetime.datetime.utcnow,
    )
    updated_at = Column(
        DateTime,
        index=False,
        unique=False,
        nullable=True,
        onupdate=datetime.datetime.utcnow,
    )
    list_id = Column(
        UUID(as_uuid=True), ForeignKey(List.id), index=True, nullable=False
    )
    list = relationship("List", back_populates="subscriptions")
