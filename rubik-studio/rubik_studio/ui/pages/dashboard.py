from __future__ import annotations

from nicegui import ui

from rubik_studio.core.audit_logger import audit
from rubik_studio.core.repository import repo_service
from rubik_studio.ui.layout import create_page_layout, empty_state


async def render() -> None:
    content = create_page_layout("Главная")
    with content:
        objects = await repo_service.list_objects()
        types = await repo_service.list_types()
        stats = await audit.get_stats()

        with ui.row().classes("w-full gap-4"):
            _stat_card("Объектов в репозитории", len(objects), "inventory_2", "bg-blue-50")
            _stat_card("Типов объектов", len(types), "category", "bg-purple-50")
            _stat_card("Записей в аудит-логе", stats.get("total", 0), "history", "bg-green-50")

        ui.separator()

        if not objects:
            empty_state(
                "inventory_2",
                "Репозиторий пуст. Создайте первый объект (роль, систему, документ или процесс), "
                "чтобы начать работу.",
                action_label="Перейти в репозиторий",
                on_action=lambda: ui.navigate.to("/repository"),
            )
        else:
            ui.label("Последние объекты").classes("text-lg font-semibold mt-4")
            recent = sorted(objects, key=lambda o: o.updated_at, reverse=True)[:10]
            with ui.list().props("bordered separator").classes("w-full"):
                for obj in recent:
                    with ui.item():
                        with ui.item_section().props("avatar"):
                            ui.icon(obj.type.icon if obj.type else "circle")
                        with ui.item_section():
                            ui.item_label(obj.name)
                            ui.item_label(obj.type.name if obj.type else "").props("caption")


def _stat_card(label: str, value: int, icon: str, bg: str) -> None:
    with ui.card().classes(f"flex-1 {bg}"):
        with ui.row().classes("items-center gap-3"):
            ui.icon(icon).classes("text-3xl text-gray-600")
            with ui.column().classes("gap-0"):
                ui.label(str(value)).classes("text-2xl font-bold")
                ui.label(label).classes("text-sm text-gray-500")
