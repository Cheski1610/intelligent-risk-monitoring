"""Convert monitored indicator changes into shared alerts."""
from __future__ import annotations

import pandas as pd

from irml.common.schemas import Alert, AlertSeverity
from irml.risk_monitoring.indicators import INDICATORS


def alerts_from_changes(
    changes: pd.DataFrame,
    *,
    indicator: str,
    limit: int = 200,
) -> list[Alert]:
    if indicator not in INDICATORS:
        raise KeyError(f"Indicador desconocido: {indicator}")
    selected = changes.loc[changes["is_alert"]].tail(limit)
    metadata = INDICATORS[indicator]
    alerts: list[Alert] = []
    for row in selected.itertuples(index=False):
        deviation = float(row.deviation_score)
        severity = (
            AlertSeverity.CRITICAL if deviation >= 7
            else AlertSeverity.HIGH if deviation >= 5
            else AlertSeverity.MEDIUM
        )
        alerts.append(
            Alert(
                source_tool="risk_monitoring",
                event_step=int(row.end_step),
                risk_category=f"cambio_temporal_{indicator}",
                score_type="review_priority",
                score_value=deviation,
                severity=severity,
                reason_codes=[
                    "robust_reference_limit_crossed",
                    f"persistent_{row.persistence}_periods",
                ],
                observed_values={
                    "indicator": indicator,
                    "label": metadata["label"],
                    "value": float(getattr(row, indicator)),
                    "direction": row.direction,
                },
                reference_values={
                    "median": float(row.reference_median),
                    "lower_limit": float(row.lower_limit),
                    "upper_limit": float(row.upper_limit),
                    "reference_periods": int(row.reference_periods)
                    if hasattr(row, "reference_periods")
                    else None,
                },
            )
        )
    return alerts
