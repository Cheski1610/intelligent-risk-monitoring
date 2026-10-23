"""Robust reference limits calculated without evaluation-period data."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(slots=True)
class RobustLimit:
    median: float
    mad: float
    scale: float
    lower: float
    upper: float
    reference_periods: int


def fit_robust_limit(
    values: pd.Series,
    *,
    multiplier: float = 3.5,
) -> RobustLimit:
    numeric = pd.to_numeric(values, errors="coerce").dropna().astype(float)
    if len(numeric) < 3:
        raise ValueError("Se requieren al menos tres periodos de referencia.")
    median = float(numeric.median())
    mad = float((numeric - median).abs().median())
    scale = 1.4826 * mad
    if scale <= 1e-12:
        scale = float(numeric.std(ddof=1))
    if scale <= 1e-12:
        scale = 0.0
    return RobustLimit(
        median=median,
        mad=mad,
        scale=scale,
        lower=median - multiplier * scale,
        upper=median + multiplier * scale,
        reference_periods=len(numeric),
    )


def reference_period_mask(
    indicators: pd.DataFrame,
    *,
    last_reference_step: int = 323,
) -> pd.Series:
    return pd.to_numeric(indicators["end_step"], errors="coerce").le(last_reference_step)
