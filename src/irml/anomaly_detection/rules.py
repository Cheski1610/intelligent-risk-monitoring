"""Deterministic robust rules fitted without evaluation labels."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(slots=True)
class RobustThreshold:
    transaction_type: str
    median: float
    mad: float
    upper_limit: float
    quantile_limit: float


class RobustAmountRules:
    def __init__(self, *, quantile: float = 0.99, mad_multiplier: float = 6.0) -> None:
        self.quantile = quantile
        self.mad_multiplier = mad_multiplier
        self.thresholds: dict[str, RobustThreshold] = {}

    def fit(self, reference: pd.DataFrame) -> dict[str, RobustThreshold]:
        valid = reference[["type", "amount"]].copy()
        valid["amount"] = pd.to_numeric(valid["amount"], errors="coerce")
        valid = valid.dropna(subset=["type", "amount"])
        valid = valid.loc[valid["amount"] >= 0]
        if valid.empty:
            raise ValueError("No hay importes válidos en el periodo de referencia.")
        for kind, group in valid.groupby("type", observed=True):
            values = group["amount"].astype(float)
            median = float(values.median())
            mad = float((values - median).abs().median())
            scale = 1.4826 * mad
            upper = median + self.mad_multiplier * scale if scale > 0 else float(values.max())
            q_limit = float(values.quantile(self.quantile))
            self.thresholds[str(kind)] = RobustThreshold(
                transaction_type=str(kind),
                median=median,
                mad=mad,
                upper_limit=max(upper, q_limit),
                quantile_limit=q_limit,
            )
        return self.thresholds

    def explain(self, frame: pd.DataFrame) -> pd.DataFrame:
        if not self.thresholds:
            raise RuntimeError("Ajuste las reglas con el periodo de referencia.")
        result = pd.DataFrame(index=frame.index)
        values = pd.to_numeric(frame["amount"], errors="coerce")
        kinds = frame["type"].astype("string")
        upper = kinds.map({kind: item.upper_limit for kind, item in self.thresholds.items()})
        quantile_limit = kinds.map(
            {kind: item.quantile_limit for kind, item in self.thresholds.items()}
        )
        median = kinds.map({kind: item.median for kind, item in self.thresholds.items()})
        mad = kinds.map({kind: item.mad for kind, item in self.thresholds.items()})
        high_amount = values.gt(upper).fillna(False)
        robust_deviation = values.gt(median + self.mad_multiplier * 1.4826 * mad).fillna(False)
        quantile_signal = values.gt(quantile_limit).fillna(False)
        result["amount_rule_alert"] = high_amount | robust_deviation | quantile_signal
        result["reason_codes"] = [
            ["amount_above_reference_threshold"] if flagged else []
            for flagged in result["amount_rule_alert"]
        ]
        result["reference_amount_limit"] = upper
        result["amount_deviation_from_median"] = values - median
        return result
