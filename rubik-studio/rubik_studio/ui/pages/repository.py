from __future__ import annotations

import asyncio

from nicegui import ui

from rubik_studio.auth.middleware import current_user
from rubik_studio.core.repository import RepositoryError, repo_service
from rubik_studio.ui.layout import confirm_dialog, create_page_layout, empty_state, show_error, show_success


async def render() -> None:
    content = create_page_layout("Репозиторий объектов")
    user = current_user() or {}

    types = await repo_service.list_types()
    type_options = {t.id: t.name for t in types}

    with content:
        with ui.row().classes("w-full items-center gap-2"):
            search_input = ui.input("Поиск по названию").classes("flex-1")
            type_select = ui.select(
                options={None: "Все типы", **type_options}, value=None, label="Тип объекта"
            ).classes("w-64")
            ui.button("Создать объект", icon="add", on_click=lambda: open_create_dialog()).props(
                "color=primary"
            )

        objects_container = ui.column().classes("w-full gap-2")

        async def refresh(_e=None) -> None:
            objects_container.clear()
            objs = await repo_service.list_objects(
                type_id=type_select.value, search=search_input.value or None
            )
            with objects_container:
                if not objs:
                    empty_state(
                        "search_off",
                        "Ничего не найдено. Измените условия поиска или создайте новый объект.",
                        action_label="Создать объект",
                        on_action=lambda: open_create_dialog(),
                    )
                    return
                with ui.list().props("bordered separator").classes("w-full"):
                    for obj in objs:
                        with ui.item():
                            with ui.item_section().props("avatar"):
                                ui.icon(obj.type.icon if obj.type else "circle").style(
                                    f"color: {obj.type.color if obj.type else '#999'}"
                                )
                            with ui.item_section():
                                ui.item_label(obj.name)
                                ui.item_label(obj.description or "").props("caption lines=1")
                            with ui.item_section().props("side"):
                                ui.label(obj.type.name if obj.type else "").classes(
                                    "text-xs text-gray-400"
                                )
                            with ui.item_section().props("side"):
                                with ui.row().classes("gap-1"):
                                    ui.button(
                                        icon="edit", on_click=lambda o=obj: open_edit_dialog(o)
                                    ).props("flat round dense")
                                    ui.button(
                                        icon="delete",
                                        on_click=lambda o=obj: ask_delete(o),
                                        color="negative",
                                    ).props("flat round dense")

        def open_create_dialog() -> None:
            if not type_options:
                show_error("Сначала должны быть доступны типы объектов. Перезапустите приложение.")
                return
            with ui.dialog() as dialog, ui.card().classes("w-96"):
                ui.label("Новый объект").classes("text-lg font-bold")
                name_input = ui.input("Название").classes("w-full")
                type_input = ui.select(options=type_options, label="Тип").classes("w-full")
                desc_input = ui.textarea("Описание").classes("w-full")
                with ui.row().classes("w-full justify-end gap-2 mt-2"):
                    ui.button("Отмена", on_click=dialog.close).props("flat")

                    async def save() -> None:
                        try:
                            await repo_service.create_object(
                                type_id=type_input.value,
                                name=name_input.value,
                                description=desc_input.value,
                                username=user.get("username", "local"),
                                user_id=user.get("id"),
                            )
                        except RepositoryError as exc:
                            show_error(str(exc))
                            return
                        dialog.close()
                        show_success("Объект создан")
                        await refresh()

                    ui.button("Сохранить", on_click=save, color="primary")
            dialog.open()

        def open_edit_dialog(obj) -> None:
            with ui.dialog() as dialog, ui.card().classes("w-96"):
                ui.label("Редактирование объекта").classes("text-lg font-bold")
                name_input = ui.input("Название", value=obj.name).classes("w-full")
                desc_input = ui.textarea("Описание", value=obj.description or "").classes("w-full")
                with ui.row().classes("w-full justify-end gap-2 mt-2"):
                    ui.button("Отмена", on_click=dialog.close).props("flat")

                    async def save() -> None:
                        try:
                            await repo_service.update_object(
                                object_id=obj.id,
                                name=name_input.value,
                                description=desc_input.value,
                                username=user.get("username", "local"),
                                user_id=user.get("id"),
                            )
                        except RepositoryError as exc:
                            show_error(str(exc))
                            return
                        dialog.close()
                        show_success("Изменения сохранены")
                        await refresh()

                    ui.button("Сохранить", on_click=save, color="primary")
            dialog.open()

        def ask_delete(obj) -> None:
            async def prepare() -> None:
                usages = await repo_service.count_usages(obj.id)
                usage_text = ""
                if usages["links"] or usages["models"]:
                    usage_text = (
                        f"\n\nИспользуется в {usages['links']} связях и "
                        f"{usages['models']} моделях."
                    )

                async def do_delete() -> None:
                    try:
                        await repo_service.delete_object(
                            obj.id,
                            username=user.get("username", "local"),
                            user_id=user.get("id"),
                        )
                    except RepositoryError as exc:
                        show_error(str(exc))
                        return
                    show_success("Объект удалён")
                    await refresh()

                confirm_dialog(
                    "Удалить объект?",
                    f'Удалить "{obj.name}"? Это действие необратимо.{usage_text}',
                    do_delete,
                )

            asyncio.create_task(prepare())

        search_input.on("keydown.enter", refresh)
        type_select.on_value_change(refresh)
        ui.button("Найти", on_click=refresh, icon="search").props("flat")

        await refresh()
