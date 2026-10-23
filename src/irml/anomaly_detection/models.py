"""Unsupervised Gaussian mixture detector with BIC model selection."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture

from irml.anomaly_detection.features import OperationalFeatureBuilder


@dataclass(slots=True)
class FitSummary:
    selected_components: int
    bic_by_components: dict[int, float]
    reference_rows: int
    invalid_reference_rows: int
    alert_quantile: float
    score_threshold: float


class GaussianMixtureDetector:
    def __init__(
        self,
        *,
        max_components: int = 5,
        seed: int = 20261021,
        alert_quantile: float = 0.995,
        max_iter: int = 100,
    ) -> None:
        if max_components < 1:
            raise ValueError("max_components debe ser positivo.")
        if not 0.5 < alert_quantile < 1:
            raise ValueError("alert_quantile debe estar entre 0.5 y 1.")
        self.max_components = max_components
        self.seed = seed
        self.alert_quantile = alert_quantile
        self.max_iter = max_iter
        self.feature_builder = OperationalFeatureBuilder()
        self.model: GaussianMixture | None = None
        self.summary: FitSummary | None = None

    def fit(self, reference: pd.DataFrame) -> FitSummary:
        matrix, valid = self.feature_builder.fit_transform(reference)
        if len(matrix) < 20:
            raise ValueError("El periodo de referencia debe contener al menos 20 filas válidas.")
        upper_components = min(self.max_components, max(1, len(matrix) // 20))
        candidates: dict[int, GaussianMixture] = {}
        bic: dict[int, float] = {}
        for components in range(1, upper_components + 1):
            model = GaussianMixture(
                n_components=components,
                covariance_type="diag",
                reg_covar=1e-5,
                n_init=1,
                max_iter=self.max_iter,
                random_state=self.seed,
            )
            model.fit(matrix)
            candidates[components] = model
            bic[components] = float(model.bic(matrix))
        selected = min(bic, key=bic.get)
        self.model = candidates[selected]
        reference_scores = -self.model.score_samples(matrix)
        threshold = float(np.quantile(reference_scores, self.alert_quantile))
        self.summary = FitSummary(
            selected_components=selected,
            bic_by_components=bic,
            reference_rows=len(matrix),
            invalid_reference_rows=int(len(reference) - int(valid.sum())),
            alert_quantile=self.alert_quantile,
            score_threshold=threshold,
        )
        return self.summary

    def score(self, frame: pd.DataFrame) -> pd.Series:
        if self.model is None:
            raise RuntimeError("Ajuste el modelo con el periodo de referencia antes de puntuar.")
        matrix, valid = self.feature_builder.transform(frame)
        scores = pd.Series(np.nan, index=frame.index, dtype="float64", name="anomaly_score")
        if len(matrix):
            scores.loc[valid] = -self.model.score_samples(matrix)
        return scores

    def flag(self, frame: pd.DataFrame) -> pd.Series:
        if self.summary is None:
            raise RuntimeError("Ajuste el modelo antes de generar alertas.")
        return (self.score(frame) >= self.summary.score_threshold).fillna(False)
