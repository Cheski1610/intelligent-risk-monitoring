"""Features available at transaction authorization time."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler


class OperationalFeatureBuilder:
    """Fit encoders and scalers on the reference period only."""

    def __init__(self) -> None:
        self.transformer = ColumnTransformer(
            transformers=[
                ("numeric", StandardScaler(), ["step", "log_amount"]),
                (
                    "type",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                    ["type"],
                ),
            ],
            remainder="drop",
            verbose_feature_names_out=False,
        )
        self._fitted = False

    @staticmethod
    def raw_features(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        needed = frame[["step", "type", "amount"]].copy()
        step = pd.to_numeric(needed["step"], errors="coerce")
        amount = pd.to_numeric(needed["amount"], errors="coerce")
        valid = (
            step.notna()
            & amount.notna()
            & amount.ge(0)
            & needed["type"].notna()
            & needed["type"].astype("string").str.strip().ne("")
        ).fillna(False)
        features = pd.DataFrame(index=frame.index)
        features["step"] = step.loc[valid].astype(float)
        features["log_amount"] = np.log1p(amount.loc[valid].astype(float))
        features["type"] = needed.loc[valid, "type"].astype(str)
        return features, valid

    def fit_transform(self, frame: pd.DataFrame) -> tuple[np.ndarray, pd.Series]:
        features, valid = self.raw_features(frame)
        if len(features) < 2:
            raise ValueError("Se necesitan al menos dos filas válidas para ajustar el detector.")
        transformed = self.transformer.fit_transform(features)
        self._fitted = True
        return np.asarray(transformed, dtype=float), valid

    def transform(self, frame: pd.DataFrame) -> tuple[np.ndarray, pd.Series]:
        if not self._fitted:
            raise RuntimeError("El transformador debe ajustarse primero con el periodo de referencia.")
        features, valid = self.raw_features(frame)
        if features.empty:
            return np.empty((0, 0), dtype=float), valid
        transformed = self.transformer.transform(features)
        return np.asarray(transformed, dtype=float), valid
