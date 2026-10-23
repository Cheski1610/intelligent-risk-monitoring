"""Reusable profiling helpers for an already loaded transaction frame."""
from __future__ import annotations

from typing import Any

import pandas as pd

from irml.data.validation import REQUIRED_COLUMNS


def profile_frame(frame: pd.DataFrame) -> dict[str, Any]:
    profile: dict[str, Any] = {
        "row_count": int(len(frame)),
        "step_min": int(frame["step"].min()) if frame["step"].notna().any() else None,
        "step_max": int(frame["step"].max()) if frame["step"].notna().any() else None,
        "transaction_types": {
            str(key): int(value)
            for key, value in frame["type"].value_counts(dropna=False).items()
        },
        "fraud_labels": {
            str(key): int(value)
            for key, value in frame["isFraud"].value_counts(dropna=False).items()
        },
        "missing_cells": {
            column: int(frame[column].isna().sum())
            for column in REQUIRED_COLUMNS
            if frame[column].isna().any()
        },
    }
    amount = frame["amount"].dropna()
    if not amount.empty:
        profile["amount"] = {
            "minimum": float(amount.min()),
            "median": float(amount.median()),
            "mean": float(amount.mean()),
            "p95": float(amount.quantile(0.95)),
            "maximum": float(amount.max()),
        }
    else:
        profile["amount"] = None
    return profile
