from __future__ import annotations

import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from rubik_studio.config import config

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(module)s:%(funcName)s:%(lineno)d | %(message)s"


def _build_system_logger() -> logging.Logger:
    logger = logging.getLogger("rubik_studio")
    logger.setLevel(getattr(logging, config.log_level, logging.INFO))
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter(LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    log_path = Path(config.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


system_log = _build_system_logger()


class AuditLogger:
    """Запись и чтение аудит-логов в БД.
    Ошибки записи аудита не должны ронять основное действие пользователя."""

    async def log(
        self,
        action: str,
        entity_type: str = "",
        entity_id: str | None = None,
        entity_name: str = "",
        user_id: str | None = None,
        username: str = "local",
        ip_address: str = "127.0.0.1",
        details: dict[str, Any] | None = None,
    ) -> None:
        if not config.audit_log_enabled:
            return
        try:
            from rubik_studio.core.database import get_session_factory
            from rubik_studio.core.models import AuditLog

            factory = get_session_factory()
            async with factory() as session:
                entry = AuditLog(
                    timestamp=datetime.now(timezone.utc),
                    user_id=user_id,
                    username=username,
                    ip_address=ip_address,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    details=details or {},
                )
                session.add(entry)
                await session.commit()
        except Exception as exc:  # noqa: BLE001
            system_log.error("Не удалось записать аудит-лог (action=%s): %s", action, exc)

    async def get_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        action: str | None = None,
        entity_type: str | None = None,
        user_id: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[dict[str, Any]]:
        from sqlalchemy import select

        from rubik_studio.core.database import get_session_factory
        from rubik_studio.core.models import AuditLog

        factory = get_session_factory()
        async with factory() as session:
            query = select(AuditLog).order_by(AuditLog.timestamp.desc())
            if action:
                query = query.where(AuditLog.action == action)
            if entity_type:
                query = query.where(AuditLog.entity_type == entity_type)
            if user_id:
                query = query.where(AuditLog.user_id == user_id)
            if date_from:
                query = query.where(AuditLog.timestamp >= date_from)
            if date_to:
                query = query.where(AuditLog.timestamp <= date_to)
            query = query.limit(limit).offset(offset)
            result = await session.execute(query)
            rows = result.scalars().all()
            return [
                {
                    "id": r.id,
                    "timestamp": r.timestamp,
                    "user_id": r.user_id,
                    "username": r.username,
                    "ip_address": r.ip_address,
                    "action": r.action,
                    "entity_type": r.entity_type,
                    "entity_id": r.entity_id,
                    "entity_name": r.entity_name,
                    "details": r.details,
                }
                for r in rows
            ]

    async def get_stats(self) -> dict[str, Any]:
        from sqlalchemy import func, select

        from rubik_studio.core.database import get_session_factory
        from rubik_studio.core.models import AuditLog

        factory = get_session_factory()
        async with factory() as session:
            total = (await session.execute(select(func.count(AuditLog.id)))).scalar_one()

            by_action_rows = await session.execute(
                select(AuditLog.action, func.count(AuditLog.id)).group_by(AuditLog.action)
            )
            by_action = {row[0]: row[1] for row in by_action_rows.all()}

            by_user_rows = await session.execute(
                select(AuditLog.username, func.count(AuditLog.id)).group_by(AuditLog.username)
            )
            by_user = {row[0]: row[1] for row in by_user_rows.all()}

            return {"total": total, "by_action": by_action, "by_user": by_user}


audit = AuditLogger()
