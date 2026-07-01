import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.types import TypeDecorator, CHAR
from database import Base


class GUID(TypeDecorator):
    """Platform-independent GUID: UUID on Postgres, CHAR(36) on SQLite."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID
            return dialect.type_descriptor(UUID())
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        return str(value) if value is not None else None

    def process_result_value(self, value, dialect):
        return str(value) if value is not None else None


def _uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id = Column(GUID, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class VerificationToken(Base):
    __tablename__ = "verification_tokens"
    id = Column(GUID, primary_key=True, default=_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)


class Plan(Base):
    __tablename__ = "plans"
    id = Column(GUID, primary_key=True, default=_uuid)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, default="My plan")
    state_json = Column(Text, nullable=False, default="{}")
    share_token = Column(String, unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
