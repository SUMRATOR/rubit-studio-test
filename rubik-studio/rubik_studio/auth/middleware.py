from __future__ import annotations

import inspect
from functools import wraps

from nicegui import app, ui

from rubik_studio.config import config


def current_user() -> dict | None:
    """В desktop-режиме возвращает фиктивного локального пользователя,
    в server-режиме — данные из сессии."""
    if not config.auth_enabled:
        return {
            "id": None,
            "username": "local",
            "display_name": "Локальный пользователь",
            "role": "admin",
        }
    return app.storage.user.get("user")


def is_authenticated() -> bool:
    if not config.auth_enabled:
        return True
    return bool(app.storage.user.get("authenticated", False))


def login_user(user_id: str, username: str, display_name: str, role: str) -> None:
    app.storage.user["authenticated"] = True
    app.storage.user["user"] = {
        "id": user_id,
        "username": username,
        "display_name": display_name,
        "role": role,
    }


def logout_user() -> None:
    app.storage.user.clear()


def require_auth(func):
    """Декоратор для страниц, требующих авторизации в server-режиме."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            ui.navigate.to("/login")
            return None
        result = func(*args, **kwargs)
        if inspect.isawaitable(result):
            return result
        return result

    return wrapper
