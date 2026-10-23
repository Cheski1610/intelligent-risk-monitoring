"""Environment-backed application configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env", override=False)


def _configured_path(variable: str, default: str) -> Path:
    value = Path(os.getenv(variable, default)).expanduser()
    return value if value.is_absolute() else PROJECT_ROOT / value


@dataclass(frozen=True, slots=True)
class Settings:
    project_root: Path = PROJECT_ROOT
    data_path: Path = _configured_path(
        "IRML_DATA_PATH", "PS_20174392719_1491204439457_log.csv"
    )
    sample_path: Path = _configured_path(
        "IRML_SAMPLE_PATH", "data/samples/paysim_demo.csv"
    )
    alert_store_path: Path = _configured_path(
        "IRML_ALERT_STORE_PATH", "data/processed/alerts.json"
    )
    sample_seed: int = int(os.getenv("IRML_SAMPLE_SEED", "20261021"))
    ollama_mode: str = os.getenv("OLLAMA_MODE", "http").strip().lower()
    ollama_base_url: str = os.getenv(
        "OLLAMA_BASE_URL", "http://localhost:11434"
    ).rstrip("/")
    ollama_docker_container: str = os.getenv(
        "OLLAMA_DOCKER_CONTAINER", "ollama"
    ).strip()
    ollama_model: str = os.getenv("OLLAMA_MODEL", "gemma4:12b").strip()
    ollama_timeout_seconds: int = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "180"))
    log_level: str = os.getenv("IRML_LOG_LEVEL", "INFO").upper()


settings = Settings()
