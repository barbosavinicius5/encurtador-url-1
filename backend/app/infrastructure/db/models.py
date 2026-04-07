"""Modelos ORM SQLAlchemy para o banco de dados."""

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Classe base para todos os modelos ORM."""

    pass


class ShortenedUrlModel(Base):
    """Modelo ORM para URLs encurtadas."""

    __tablename__ = "shortened_urls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    original_url = Column(String, nullable=False)
    short_code = Column(String(20), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    click_count = Column(Integer, nullable=False, default=0, server_default="0")
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    session_id = Column(String(36), nullable=True, index=True)

    __table_args__ = (Index("ix_shortened_urls_session_id", "session_id"),)


class ApiKeyModel(Base):
    """Modelo ORM para chaves de acesso à API."""

    __tablename__ = "api_keys"

    id = Column(String, primary_key=True)
    key = Column(String, nullable=False, unique=True, index=True)
    owner = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_api_keys_key", "key"),)
