from __future__ import annotations

import json
import logging
import secrets
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger("rubik_studio")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CONFIG_PATH = DATA_DIR / "config.json"
CONFIG_BACKUP_PATH = DATA_DIR / "config.json.bak"


@dataclass
class AppConfig:
    mode: str = "desktop"  # "desktop" | "server"
    host: str = "127.0.0.1"
    port: int = 8080
    db_type: str = "sqlite"  # "sqlite" | "postgresql"
    db_path: str = str(DATA_DIR / "rubik_studio.db")
    db_url: str = ""
    auth_enabled: bool = False
    secret_key: str = field(default_factory=lambda: secrets.token_hex(32))
    log_level: str = "INFO"
    audit_log_enabled: bool = True
    log_file: str = str(DATA_DIR / "app.log")
    first_run_done: bool = False

    def get_db_url(self) -> str:
        if self.db_type == "postgresql" and self.db_url:
            return self.db_url
        path = Path(self.db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite+aiosqlite:///{path.as_posix()}"

    def switch_to_server(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        self.mode = "server"
        self.host = host
        self.port = port
        self.auth_enabled = True
        self.save()

    def switch_to_desktop(self) -> None:
        self.mode = "desktop"
        self.host = "127.0.0.1"
        self.auth_enabled = False
        self.save()

    def save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            if CONFIG_PATH.exists():
                CONFIG_PATH.replace(CONFIG_BACKUP_PATH)
        except OSError as exc:
            logger.warning("Не удалось создать резервную копию конфига: %s", exc)
        try:
            with CONFIG_PATH.open("w", encoding="utf-8") as fh:
                json.dump(asdict(self), fh, ensure_ascii=False, indent=2)
        except OSError as exc:
            logger.error("Не удалось сохранить конфигурацию: %s", exc)

    @classmethod
    def load(cls) -> "AppConfig":
        if not CONFIG_PATH.exists():
            cfg = cls()
            cfg.save()
            return cfg
        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as fh:
                raw = json.load(fh)
            known = set(cls.__dataclass_fields__)
            return cls(**{k: v for k, v in raw.items() if k in known})
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Файл настроек повреждён (%s). Использую настройки по умолчанию.", exc)
            if CONFIG_BACKUP_PATH.exists():
                try:
                    with CONFIG_BACKUP_PATH.open("r", encoding="utf-8") as fh:
                        raw = json.load(fh)
                    known = set(cls.__dataclass_fields__)
                    logger.info("Настройки восстановлены из резервной копии.")
                    return cls(**{k: v for k, v in raw.items() if k in known})
                except (json.JSONDecodeError, OSError):
                    pass
            return cls()


config = AppConfig.load()
