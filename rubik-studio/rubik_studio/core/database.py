from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from rubik_studio.config import config
from rubik_studio.core.audit_logger import system_log


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(config.get_db_url(), echo=False, future=True)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(), expire_on_commit=False, class_=AsyncSession
        )
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        yield session


def backup_database(keep: int = 3) -> None:
    """Копирует файл БД SQLite в .bak перед запуском (ротация keep последних)."""
    if config.db_type != "sqlite":
        return
    db_file = Path(config.db_path)
    if not db_file.exists():
        return
    try:
        for i in range(keep - 1, 0, -1):
            src = db_file.with_suffix(db_file.suffix + f".bak{i}")
            dst = db_file.with_suffix(db_file.suffix + f".bak{i + 1}")
            if src.exists():
                shutil.copy2(src, dst)
        shutil.copy2(db_file, db_file.with_suffix(db_file.suffix + ".bak1"))
        system_log.info("Создана резервная копия БД.")
    except OSError as exc:
        system_log.warning("Не удалось создать резервную копию БД: %s", exc)


def check_integrity() -> bool:
    """Проверка целостности SQLite через PRAGMA integrity_check."""
    if config.db_type != "sqlite":
        return True
    db_file = Path(config.db_path)
    if not db_file.exists():
        return True
    try:
        conn = sqlite3.connect(str(db_file))
        try:
            cursor = conn.execute("PRAGMA integrity_check;")
            result = cursor.fetchone()
            ok = bool(result) and result[0] == "ok"
            if not ok:
                system_log.error("Проверка целостности БД не пройдена: %s", result)
            return ok
        finally:
            conn.close()
    except sqlite3.Error as exc:
        system_log.error("Ошибка при проверке целостности БД: %s", exc)
        return False


async def init_db() -> None:
    """Создаёт таблицы (если их нет) и наполняет начальными данными."""
    from rubik_studio.core import models  # noqa: F401  регистрация моделей в метаданных

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _seed_data()
    system_log.info("База данных инициализирована: %s", config.get_db_url())


async def _seed_data() -> None:
    from sqlalchemy import select

    from rubik_studio.auth.users import hash_password
    from rubik_studio.core.models import ObjectType, User

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(ObjectType))
        if result.first() is None:
            seed_types = [
                ("ROLE", "Роль", "person", "#1976D2"),
                ("SYSTEM", "Информационная система", "computer", "#5E35B1"),
                ("DOCUMENT", "Документ", "description", "#F9A825"),
                ("PROCESS", "Процесс", "account_tree", "#2E7D32"),
                ("RISK", "Риск", "warning", "#C62828"),
                ("KPI", "Показатель (KPI)", "trending_up", "#00838F"),
                ("DEPARTMENT", "Подразделение", "apartment", "#6D4C41"),
            ]
            for code, name, icon, color in seed_types:
                session.add(ObjectType(code=code, name=name, icon=icon, color=color))

        result = await session.execute(select(User).where(User.username == "admin"))
        if result.scalar_one_or_none() is None:
            session.add(
                User(
                    username="admin",
                    display_name="Администратор",
                    password_hash=hash_password("admin"),
                    role="admin",
                    is_active=True,
                )
            )
        await session.commit()
