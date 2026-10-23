"""Alert ranking and conversion into the shared alert contract."""
from __future__ import annotations

import pandas as pd

from irml.common.schemas import Alert, AlertSeverity


def severity_for_rank(rank: int, total: int) -> AlertSeverity:
    if total <= 0:
        return AlertSeverity.INFORMATIONAL
    percentile = rank / total
    if percentile >= 0.995:
        return AlertSeverity.CRITICAL
    if percentile >= 0.98:
        return AlertSeverity.HIGH
    if percentile >= 0.90:
        return AlertSeverity.MEDIUM
    return AlertSeverity.LOW


def build_anomaly_alerts(
    frame: pd.DataFrame,
    scores: pd.Series,
    flags: pd.Series,
    *,
    limit: int = 500,
    reason_codes: pd.Series | None = None,
) -> list[Alert]:
    candidates = frame.loc[flags.fillna(False)].copy()
    candidates["anomaly_score"] = scores.reindex(candidates.index)
    candidates = candidates.dropna(subset=["anomaly_score"]).nlargest(limit, "anomaly_score")
    alerts: list[Alert] = []
    total = max(1, len(candidates))
    selected_threshold = float(candidates["anomaly_score"].min()) if len(candidates) else None
    for rank, (index, row) in enumerate(candidates.iterrows(), start=1):
        raw_reasons = reason_codes.loc[index] if reason_codes is not None else []
        if not isinstance(raw_reasons, list):
            raw_reasons = [str(raw_reasons)]
        reasons = list(dict.fromkeys(["gmm_low_likelihood", *raw_reasons]))
        score = float(row["anomaly_score"])
        source_id = row.get("_source_row_id")
        alerts.append(
            Alert(
                source_tool="anomaly_detection",
                event_step=int(row["step"]) if pd.notna(row.get("step")) else None,
                transaction_id=str(source_id) if pd.notna(source_id) else None,
                risk_category="comportamiento_transaccional_inusual",
                score_type="anomaly_score",
                score_value=score,
                severity=severity_for_rank(total - rank + 1, total),
                reason_codes=reasons,
                observed_values={
                    "type": str(row.get("type")),
                    "amount": float(row["amount"]) if pd.notna(row.get("amount")) else None,
                    "anomaly_score": score,
                },
                reference_values={"selected_alert_floor": selected_threshold},
            )
        )
    return alerts
