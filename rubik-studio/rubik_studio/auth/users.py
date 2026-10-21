from __future__ import annotations

from passlib.context import CryptContext
from sqlalchemy import select

from rubik_studio.core.audit_logger import audit
from rubik_studio.core.database import get_session_factory
from rubik_studio.core.models import User
from rubik_studio.core.validators import validate_role, validate_user_credentials

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _pwd_context.verify(password, password_hash)
    except ValueError:
        return False


class AuthError(Exception):
    """Ошибка аутентификации/управления пользователями. Сообщение — человекочитаемое."""


async def authenticate(username: str, password: str, ip_address: str = "127.0.0.1") -> User | None:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        await audit.log(
            action="LOGIN",
            entity_type="User",
            username=username or "unknown",
            ip_address=ip_address,
            details={"success": False},
        )
        return None

    await audit.log(
        action="LOGIN",
        entity_type="User",
        entity_id=user.id,
        entity_name=user.display_name,
        user_id=user.id,
        username=user.username,
        ip_address=ip_address,
        details={"success": True},
    )
    return user


async def list_users() -> list[User]:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(select(User).order_by(User.username))
        return list(result.scalars().all())


async def create_user(
    username: str,
    password: str,
    display_name: str,
    role: str = "user",
    acting_username: str = "local",
    acting_user_id: str | None = None,
) -> User:
    is_valid, message = validate_user_credentials(username, password)
    if not is_valid:
        raise AuthError(message)
    is_valid, message = validate_role(role)
    if not is_valid:
        raise AuthError(message)

    factory = get_session_factory()
    async with factory() as session:
        existing = await session.execute(select(User).where(User.username == username))
        if existing.scalar_one_or_none() is not None:
            raise AuthError("Пользователь с таким логином уже существует")

        user = User(
            username=username,
            display_name=display_name or username,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    await audit.log(
        action="CREATE",
        entity_type="User",
        entity_id=user.id,
        entity_name=user.username,
        user_id=acting_user_id,
        username=acting_username,
    )
    return user


async def delete_user(user_id: str, acting_user_id: str, acting_username: str = "local") -> None:
    if user_id == acting_user_id:
        raise AuthError("Нельзя удалить свою учётную запись")

    factory = get_session_factory()
    async with factory() as session:
        user = await session.get(User, user_id)
        if user is None:
            raise AuthError("Пользователь не найден")

        if user.role == "admin":
            admins = await session.execute(
                select(User).where(User.role == "admin", User.is_active == True)  # noqa: E712
            )
            if len(admins.scalars().all()) <= 1:
                raise AuthError("Нельзя удалить единственного администратора")

        name = user.username
        await session.delete(user)
        await session.commit()

    await audit.log(
        action="DELETE",
        entity_type="User",
        entity_id=user_id,
        entity_name=name,
        user_id=acting_user_id,
        username=acting_username,
    )
