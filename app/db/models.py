from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    avatar_path: Mapped[str] = mapped_column(String(255))
    profile_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    draft_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    draft_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    draft_avatar_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    draft_profile_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    profile_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    config_status: Mapped[str] = mapped_column(String(20), default="published", nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    character_id: Mapped[int] = mapped_column(ForeignKey("characters.id"), index=True)
    relationship_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    emotion_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    scene_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    __table_args__ = (
        Index("ix_conversations_user_character", "user_id", "character_id", unique=True),
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    message_type: Mapped[str] = mapped_column(String(20))
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audio_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audio_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id"), index=True
    )
    memory_type: Mapped[str] = mapped_column(String(40))
    content: Mapped[str] = mapped_column(Text)
    importance: Mapped[int] = mapped_column(Integer, default=3)
    source_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        Index("ix_memories_conversation_active", "conversation_id", "is_active"),
    )
