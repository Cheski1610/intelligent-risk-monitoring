"""CSV and JSON serialization for alert and indicator downloads."""
from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd
from pydantic import BaseModel


def records_to_frame(records: Iterable[BaseModel | Mapping[str, Any]]) -> pd.DataFrame:
    rows = [
        item.model_dump(mode="json") if isinstance(item, BaseModel) else dict(item)
        for item in records
    ]
    return pd.DataFrame(rows)


def csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8-sig")


def json_bytes(records: Iterable[BaseModel | Mapping[str, Any]]) -> bytes:
    normalized = [
        item.model_dump(mode="json") if isinstance(item, BaseModel) else dict(item)
        for item in records
    ]
    return json.dumps(normalized, ensure_ascii=False, indent=2).encode("utf-8")
