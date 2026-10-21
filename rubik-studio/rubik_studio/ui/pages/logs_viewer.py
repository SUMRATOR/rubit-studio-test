from __future__ import annotations

from nicegui import ui

from rubik_studio.core.audit_logger import audit
from rubik_studio.ui.layout import create_page_layout, empty_state


async def render() -> None:
    content = create_page_layout("Аудит-логи")
    with content:
        stats = await audit.get_stats()
        ui.label(f"Всего записей: {stats.get('total', 0)}").classes("text-sm text-gray-500")

        logs = await audit.get_logs(limit=200)
        if not logs:
            empty_state(
                "history",
                "Аудит-логи пока пусты. Действия пользователей будут отображаться здесь.",
            )
            return

        columns = [
            {"name": "timestamp", "label": "Время", "field": "timestamp", "align": "left"},
            {"name": "username", "label": "Пользователь", "field": "username", "align": "left"},
            {"name": "action", "label": "Действие", "field": "action", "align": "left"},
            {"name": "entity_type", "label": "Объект", "field": "entity_type", "align": "left"},
            {"name": "entity_name", "label": "Название", "field": "entity_name", "align": "left"},
        ]
        rows = [
            {
                "timestamp": log["timestamp"].strftime("%Y-%m-%d %H:%M:%S") if log["timestamp"] else "",
                "username": log["username"],
                "action": log["action"],
                "entity_type": log["entity_type"],
                "entity_name": log["entity_name"],
            }
            for log in logs
        ]
        ui.table(columns=columns, rows=rows, row_key="timestamp").classes("w-full")
