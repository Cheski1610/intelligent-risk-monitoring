"""Hourly and simulated-day indicators with optional sample expansion weights."""
from __future__ import annotations

import pandas as pd


def load_expansion_weights(path: str) -> dict[int, float]:
    table = pd.read_csv(path)
    required = {"step", "expansion_weight"}
    if not required.issubset(table.columns):
        raise ValueError(f"El perfil por paso requiere las columnas {sorted(required)}.")
    return {
        int(row.step): float(row.expansion_weight)
        for row in table.itertuples(index=False)
    }


def aggregate_indicators(
    frame: pd.DataFrame,
    *,
    granularity: str = "hour",
    expansion_weights: dict[int, float] | None = None,
) -> pd.DataFrame:
    """Aggregate observed sample counts and weighted volume estimates."""
    if granularity not in {"hour", "day"}:
        raise ValueError("granularity debe ser 'hour' o 'day'.")
    working = frame[["step", "amount", "nameOrig", "nameDest"]].copy()
    working["step"] = pd.to_numeric(working["step"], errors="coerce")
    working["amount"] = pd.to_numeric(working["amount"], errors="coerce")
    working = working.dropna(subset=["step", "amount"])
    if working.empty:
        return pd.DataFrame(
            columns=[
                "period", "end_step", "sample_count", "estimated_transaction_count",
                "estimated_amount_sum", "mean_amount", "p95_amount", "active_origins",
                "top_destination_share", "alert_rate",
            ]
        )
    working["step"] = working["step"].astype(int)
    if granularity == "hour":
        working["period"] = working["step"]
    else:
        working["period"] = ((working["step"] - 1) // 24) + 1
    weights = expansion_weights or {}
    working["_expansion_weight"] = working["step"].map(weights).fillna(1.0).astype(float)
    if "_anomaly_flag" in frame.columns:
        working["_alert_flag"] = frame.loc[working.index, "_anomaly_flag"].fillna(False).astype(bool)
    else:
        working["_alert_flag"] = False

    records: list[dict[str, float | int]] = []
    for period, group in working.groupby("period", sort=True, observed=True):
        destination_counts = group["nameDest"].value_counts(dropna=True)
        sample_count = len(group)
        records.append(
            {
                "period": int(period),
                "end_step": int(group["step"].max()),
                "sample_count": sample_count,
                "estimated_transaction_count": float(group["_expansion_weight"].sum()),
                "estimated_amount_sum": float(
                    (group["amount"] * group["_expansion_weight"]).sum()
                ),
                "mean_amount": float(group["amount"].mean()),
                "p95_amount": float(group["amount"].quantile(0.95)),
                "active_origins": int(group["nameOrig"].nunique(dropna=True)),
                "top_destination_share": (
                    float(destination_counts.iloc[0] / sample_count)
                    if len(destination_counts) and sample_count
                    else 0.0
                ),
                "alert_rate": float(group["_alert_flag"].mean()) if sample_count else 0.0,
            }
        )
    return pd.DataFrame.from_records(records)
