from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rubik_studio.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Репозиторий объектов ────────────────────────────────────────────────────


class ObjectType(Base):
    __tablename__ = "object_types"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    icon: Mapped[str] = mapped_column(String(50), default="circle")
    color: Mapped[str] = mapped_column(String(7), default="#9E9E9E")

    objects: Mapped[list["Object"]] = relationship(back_populates="type")


class Object(Base):
    __tablename__ = "objects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    type_id: Mapped[str] = mapped_column(String(36), ForeignKey("object_types.id"))
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    type: Mapped["ObjectType"] = relationship(back_populates="objects", lazy="selectin")


class ObjectLink(Base):
    __tablename__ = "object_links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    source_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("objects.id", ondelete="CASCADE")
    )
    target_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("objects.id", ondelete="CASCADE")
    )
    link_type: Mapped[str] = mapped_column(String(50), nullable=False)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)


# ── BPMN (используется с Этапа 2) ───────────────────────────────────────────


class BpmnModel(Base):
    __tablename__ = "bpmn_models"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    xml_content: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class ModelElementBinding(Base):
    __tablename__ = "model_element_bindings"
    __table_args__ = (UniqueConstraint("model_id", "bpmn_element_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    model_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("bpmn_models.id", ondelete="CASCADE")
    )
    bpmn_element_id: Mapped[str] = mapped_column(String(200), nullable=False)
    object_id: Mapped[str] = mapped_column(String(36), ForeignKey("objects.id"))


# ── Process Mining (используется с Этапа 3) ─────────────────────────────────


class EventLog(Base):
    __tablename__ = "event_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (Index("ix_events_log_case_ts", "log_id", "case_id", "timestamp"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    log_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("event_logs.id", ondelete="CASCADE")
    )
    case_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    activity: Mapped[str] = mapped_column(String(500), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resource: Mapped[str | None] = mapped_column(String(200), nullable=True)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)


# ── Пользователи и аудит ─────────────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_user_ts", "user_id", "timestamp"),
        Index("ix_audit_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, index=True
    )
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    username: Mapped[str] = mapped_column(String(100), default="local")
    ip_address: Mapped[str] = mapped_column(String(45), default="127.0.0.1")
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), default="")
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    entity_name: Mapped[str] = mapped_column(String(500), default="")
    details: Mapped[dict] = mapped_column(JSON, default=dict)


# ── BPMS (используется с Этапа 4) ───────────────────────────────────────────


class ProcessDefinition(Base):
    __tablename__ = "process_definitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("bpmn_models.id"))
    code: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ProcessInstance(Base):
    __tablename__ = "process_instances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    definition_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("process_definitions.id")
    )
    status: Mapped[str] = mapped_column(String(20), default="RUNNING")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    variables: Mapped[dict] = mapped_column(JSON, default=dict)
    spiff_state: Mapped[str | None] = mapped_column(Text, nullable=True)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    process_instance_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("process_instances.id", ondelete="CASCADE")
    )
    bpmn_task_id: Mapped[str] = mapped_column(String(200), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="READY")
    assignee_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    assignee_name: Mapped[str] = mapped_column(String(200), default="")
    candidate_group: Mapped[str | None] = mapped_column(String(100), nullable=True)
    form_data: Mapped[dict] = mapped_column(JSON, default=dict)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TaskHistory(Base):
    __tablename__ = "task_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(50))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
