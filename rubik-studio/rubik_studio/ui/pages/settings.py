from __future__ import annotations

from nicegui import ui

from rubik_studio.auth.middleware import current_user
from rubik_studio.auth.users import AuthError, create_user, delete_user, list_users
from rubik_studio.config import config
from rubik_studio.ui.layout import confirm_dialog, create_page_layout, show_error, show_success, show_warning


async def render() -> None:
    content = create_page_layout("Настройки")
    user = current_user() or {}

    with content:
        with ui.card().classes("w-full"):
            ui.label("Режим работы").classes("text-lg font-semibold")
            ui.label(
                f"Текущий режим: {'Desktop (локально)' if config.mode == 'desktop' else 'Server (сеть)'}"
            ).classes("text-sm text-gray-600")
            ui.label(f"База данных: {config.db_type}").classes("text-sm text-gray-500")

            with ui.row().classes("gap-2 mt-2"):
                if config.mode == "desktop":
                    ui.button(
                        "Переключить в Server-режим",
                        icon="cloud",
                        on_click=lambda: confirm_switch("server"),
                    ).props("color=primary")
                else:
                    ui.button(
                        "Переключить в Desktop-режим",
                        icon="computer",
                        on_click=lambda: confirm_switch("desktop"),
                    ).props("color=primary")

        if config.mode == "server" and user.get
