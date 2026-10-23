"""Local, explicit persistence for alerts shared across app entry points."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from irml.common.schemas import Alert


def save_alerts(alerts: Iterable[Alert], path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = [alert.model_dump(mode="json") for alert in alerts]
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(destination)
    return destination


def upsert_alerts(
    alerts: Iterable[Alert],
    path: str | Path,
    *,
    source_tool: str,
) -> Path:
    existing = [
        alert
        for alert in load_alerts(path)
        if alert.source_tool != source_tool
    ]
    return save_alerts([*existing, *alerts], path)


def load_alerts(path: str | Path) -> list[Alert]:
    source = Path(path)
    if not source.is_file():
        return []
    raw = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("El archivo de alertas debe contener una lista JSON.")
    return [Alert.model_validate(item) for item in raw]
