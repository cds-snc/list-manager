import datetime
import uuid

from sqlalchemy import DateTime, Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates


from models import Base


class List(Base):
    __tablename__ = "lists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    language = Column(String, nullable=False, index=False)
    subscribe_email_template_id = Column(String)
    unsubscribe_email_template_id = Column(String)
    subscribe_phone_template_id = Column(String)
    unsubscribe_phone_template_id = Column(String)
    service_id = Column(String, nullable=False, index=True)
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

    subscriptions = relationship("Subscription", cascade="all,delete")

    @validates("name")
    def validate_name(self, _key, value):
        assert value != ""
        return value

    @validates("language")
    def validate_language(self, _key, value):
        assert value != ""
        return value.lower()

    @validates("service_id")
    def validate_service_id(self, _key, value):
        assert value != ""
        return value.lower()
