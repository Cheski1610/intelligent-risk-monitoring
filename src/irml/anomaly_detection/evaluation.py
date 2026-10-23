"""Retrospective metrics for anomaly scores and fixed alert thresholds."""
from __future__ import annotations

import math
from typing import Any

import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def evaluate_scores(
    labels: pd.Series,
    scores: pd.Series,
    *,
    threshold: float,
    top_k_fraction: float = 0.01,
) -> dict[str, Any]:
    """Evaluate scores after aligning rows and excluding invalid labels/scores.

    ``threshold`` must have been selected using reference data; labels are used
    here only for retrospective evaluation. Accuracy is intentionally omitted
    because it can obscure performance on a highly imbalanced dataset.
    """
    if not 0 < top_k_fraction <= 1:
        raise ValueError("top_k_fraction debe estar en el intervalo (0, 1].")

    aligned_scores = pd.to_numeric(scores.reindex(labels.index), errors="coerce")
    aligned_labels = pd.to_numeric(labels, errors="coerce")
    valid = (
        aligned_labels.isin([0, 1])
        & aligned_scores.notna()
        & aligned_scores.map(math.isfinite)
    )
    y_true = aligned_labels.loc[valid].astype(int)
    y_score = aligned_scores.loc[valid].astype(float)
    n_rows = len(y_true)
    positive_labels = int(y_true.sum())

    if not n_rows:
        return {
            "evaluated_rows": 0,
            "positive_labels": 0,
            "alert_count": 0,
            "alert_rate": 0.0,
            "precision": None,
            "recall": None,
            "f1": None,
            "pr_auc": None,
            "roc_auc": None,
            "precision_at_k": None,
            "recall_at_k": None,
        }

    predicted = y_score.ge(threshold)
    alert_count = int(predicted.sum())
    precision_at_threshold = float(precision_score(y_true, predicted, zero_division=0))
    recall_at_threshold = float(recall_score(y_true, predicted, zero_division=0))
    f1_at_threshold = float(f1_score(y_true, predicted, zero_division=0))

    k = max(1, math.ceil(n_rows * top_k_fraction))
    top_indices = y_score.nlargest(k).index
    top_k_positives = int(y_true.loc[top_indices].sum())
    precision_at_k = top_k_positives / k
    recall_at_k = top_k_positives / positive_labels if positive_labels else None

    return {
        "evaluated_rows": n_rows,
        "positive_labels": positive_labels,
        "alert_count": alert_count,
        "alert_rate": alert_count / n_rows,
        "precision": precision_at_threshold,
        "recall": recall_at_threshold,
        "f1": f1_at_threshold,
        "pr_auc": float(average_precision_score(y_true, y_score))
        if positive_labels
        else None,
        "roc_auc": float(roc_auc_score(y_true, y_score))
        if y_true.nunique() == 2
        else None,
        "precision_at_k": precision_at_k,
        "recall_at_k": recall_at_k,
        "top_k_count": k,
    }
