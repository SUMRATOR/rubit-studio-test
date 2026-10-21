from __future__ import annotations

from typing import Callable

from nicegui import ui

from rubik_studio.config import config


def render(on_finish: Callable[[], None]) -> None:
    with ui.dialog().props("persistent") as dialog, ui.card().classes("w-[32rem]"):
        ui.icon("waving_hand").classes("text-5xl text-primary")
        ui.label("Добро пожаловать в Rubik Studio!").classes("text-xl font-bold")
        ui.label(
            "Rubik Studio — инструмент для моделирования, анализа и автоматизации "
            "бизнес-процессов. Здесь вы сможете:"
        ).classes("text-sm text-gray-600")
        with ui.list():
            for text in [
                "📁 Вести репозиторий ролей, систем, документов и процессов",
                "🔀 Рисовать BPMN-схемы процессов",
                "📊 Анализировать журналы событий (Process Mining)",
                "⚙️ Запускать и исполнять процессы (BPMS)",
            ]:
                ui.item(text)
        ui.label("Начните с создания первого объекта в разделе «Репозиторий».").classes(
            "text-sm text-gray-500 mt-2"
        )

        def finish() -> None:
            config.first_run_done = True
            config.save()
            dialog.close()
            on_finish()

        ui.button("Начать работу", on_click=finish, icon="arrow_forward").classes(
            "w-full mt-4"
        ).props("color=primary")
    dialog.open()
