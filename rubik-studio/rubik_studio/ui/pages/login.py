from __future__ import annotations

from nicegui import ui

from rubik_studio.auth.middleware import login_user
from rubik_studio.auth.users import authenticate
from rubik_studio.ui.layout import show_error


def render() -> None:
    with ui.column().classes("absolute-center items-center gap-4"):
        ui.icon("view_in_ar").classes("text-5xl text-primary")
        ui.label("RS — RUBIK STUDIO").classes("text-2xl font-bold")
        ui.label("Model. Mine. Automate.").classes("text-sm text-gray-500 mb-4")

        with ui.card().classes("w-80"):
            username_input = ui.input("Логин").classes("w-full")
            password_input = ui.input("Пароль", password=True).classes("w-full")

            async def do_login() -> None:
                user = await authenticate(username_input.value, password_input.value)
                if user is None:
                    show_error("Неверный логин или пароль")
                    return
                login_user(user.id, user.username, user.display_name, user.role)
                ui.navigate.to("/")

            password_input.on("keydown.enter", do_login)
            ui.button("Войти", on_click=do_login, icon="login").classes("w-full mt-2").props(
                "color=primary"
            )
