from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

MAX_NAME_LENGTH = 500
MAX_DESCRIPTION_LENGTH = 10_000
MAX_BPMN_SIZE_BYTES = 5 * 1024 * 1024
MAX_CSV_SIZE_BYTES = 100 * 1024 * 1024
MIN_EVENTS_COUNT = 10

BPMN_NAMESPACE = "http://www.omg.org/spec/BPMN/20100524/MODEL"

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.]{3,50}$")
WEAK_PASSWORDS = {"admin", "password", "123456", "qwerty", "111111", "12345678"}

VALID_TASK_STATUSES_FOR_COMPLETION = {"READY", "CLAIMED", "IN_PROGRESS"}
VALID_ROLES = {"admin", "user", "viewer"}


def validate_object_name(name: str | None) -> tuple[bool, str]:
    if name is None or not name.strip():
        return False, "Название не может быть пустым"
    if len(name) > MAX_NAME_LENGTH:
        return False, f"Название слишком длинное (макс. {MAX_NAME_LENGTH} символов)"
    return True, ""


def validate_description(description: str | None) -> tuple[bool, str]:
    if description and len(description) > MAX_DESCRIPTION_LENGTH:
        return False, f"Описание слишком длинное (макс. {MAX_DESCRIPTION_LENGTH} символов)"
    return True, ""


def validate_link(source_id: str, target_id: str) -> tuple[bool, str]:
    if source_id == target_id:
        return False, "Объект не может быть связан сам с собой"
    return True, ""


def validate_bpmn_xml(xml_content: str) -> tuple[bool, str]:
    if not xml_content or not xml_content.strip():
        return False, "Модель не содержит ни одного процесса"
    if len(xml_content.encode("utf-8")) > MAX_BPMN_SIZE_BYTES:
        return False, "Модель слишком большая (макс. 5 МБ)"
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return False, "Файл не является корректным XML"

    if not (root.tag.startswith("{" + BPMN_NAMESPACE + "}") or "definitions" in root.tag):
        return False, "Файл не является BPMN-документом"

    processes = root.findall(f"{{{BPMN_NAMESPACE}}}process")
    if not processes:
        return False, "Модель не содержит ни одного процесса"

    has_start_event = any(
        proc.find(f"{{{BPMN_NAMESPACE}}}startEvent") is not None for proc in processes
    )
    if not has_start_event:
        return False, "Процесс не имеет начального события"

    return True, ""


def validate_csv_file(file_path: str | Path, size_bytes: int) -> tuple[bool, str]:
    path = Path(file_path)
    if path.suffix.lower() != ".csv":
        return False, "Поддерживаются только CSV-файлы"
    if size_bytes == 0:
        return False, "Файл пуст"
    if size_bytes > MAX_CSV_SIZE_BYTES:
        return False, "Файл слишком большой (макс. 100 МБ)"
    return True, ""


def validate_csv_columns(columns: list[str]) -> tuple[bool, str]:
    required = {"case_id", "activity", "timestamp"}
    missing = required - set(columns)
    if missing:
        return False, f"Отсутствуют обязательные колонки: {', '.join(sorted(missing))}. Настройте маппинг"
    return True, ""


def validate_event_count(count: int) -> tuple[bool, str]:
    if count < MIN_EVENTS_COUNT:
        return False, f"Слишком мало событий (мин. {MIN_EVENTS_COUNT}). Загружено: {count}"
    return True, ""


def validate_user_credentials(username: str, password: str) -> tuple[bool, str]:
    if not USERNAME_RE.match(username or ""):
        return False, "Логин: 3–50 символов, латинские буквы, цифры, «_» и «.»"
    if not password or len(password) < 6:
        return False, "Пароль слишком короткий (мин. 6 символов)"
    if password.lower() in WEAK_PASSWORDS:
        return False, "Пароль слишком простой. Используйте более сложный пароль"
    return True, ""


def validate_role(role: str) -> tuple[bool, str]:
    if role not in VALID_ROLES:
        return False, "Выберите роль из списка: admin, user, viewer"
    return True, ""


def validate_task_action(
    task_status: str, user_id: str | None, assignee_id: str | None
) -> tuple[bool, str]:
    if task_status not in VALID_TASK_STATUSES_FOR_COMPLETION:
        return False, "Задача уже завершена или отменена"
    if assignee_id and user_id and assignee_id != user_id:
        return False, "Задача назначена другому пользователю"
    return True, ""


def validate_deadline(due_date: datetime | None) -> tuple[bool, str]:
    if due_date is None:
        return True, ""
    now = datetime.now(due_date.tzinfo or timezone.utc)
    if due_date < now:
        return False, "Дедлайн не может быть в прошлом"
    return True, ""
