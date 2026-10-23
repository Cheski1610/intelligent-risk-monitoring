"""Transparent robust threshold and persistence checks."""
from __future__ import annotations

import pandas as pd

from irml.risk_monitoring.thresholds import RobustLimit, fit_robust_limit, reference_period_mask


def detect_changes(
    indicators: pd.DataFrame,
    indicator: str,
    *,
    last_reference_step: int = 323,
    multiplier: float = 3.5,
    minimum_persistence: int = 2,
) -> tuple[pd.DataFrame, RobustLimit]:
    if indicator not in indicators:
        raise KeyError(f"Indicador desconocido: {indicator}")
    if minimum_persistence < 1:
        raise ValueError("minimum_persistence debe ser al menos 1.")
    baseline_mask = reference_period_mask(
        indicators, last_reference_step=last_reference_step
    )
    reference = indicators.loc[baseline_mask, indicator]
    limit = fit_robust_limit(reference, multiplier=multiplier)

    result = indicators[["period", "end_step", indicator]].copy()
    result["reference_median"] = limit.median
    result["lower_limit"] = limit.lower
    result["upper_limit"] = limit.upper
    values = pd.to_numeric(result[indicator], errors="coerce")
    result["reference_periods"] = limit.reference_periods
    result["deviation_score"] = (values - limit.median).abs() / max(limit.scale, 1e-12)
    result["crossed_threshold"] = (
        (values < limit.lower) | (values > limit.upper)
    ).fillna(False)
    persistence: list[int] = []
    streak = 0
    for crossed in result["crossed_threshold"]:
        streak = streak + 1 if crossed else 0
        persistence.append(streak)
    result["persistence"] = persistence
    result["is_alert"] = (
        result["crossed_threshold"]
        & result["persistence"].ge(minimum_persistence)
    )
    result["direction"] = values.gt(limit.upper).map(
        {True: "aumento", False: "disminución"}
    )
    return result, limit
