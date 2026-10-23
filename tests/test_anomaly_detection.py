from __future__ import annotations

import pytest

from irml.anomaly_detection.evaluation import evaluate_scores
from irml.anomaly_detection.features import OperationalFeatureBuilder
from irml.anomaly_detection.models import GaussianMixtureDetector


def test_feature_builder_excludes_labels_balances_and_identifiers(transactions):
    builder = OperationalFeatureBuilder()
    matrix, valid = builder.fit_transform(transactions)

    fitted_columns = builder.transformer.get_feature_names_out().tolist()
    assert len(matrix) == int(valid.sum())
    assert all(
        forbidden not in " ".join(fitted_columns)
        for forbidden in (
            "isFraud",
            "isFlaggedFraud",
            "oldbalanceOrg",
            "newbalanceOrig",
            "oldbalanceDest",
            "newbalanceDest",
            "nameOrig",
            "nameDest",
        )
    )


def test_gmm_is_reproducible_and_fits_reference_only(transactions):
    reference = transactions.loc[transactions["step"] <= 70]
    first = GaussianMixtureDetector(max_components=2, seed=41, max_iter=30)
    second = GaussianMixtureDetector(max_components=2, seed=41, max_iter=30)

    first_summary = first.fit(reference)
    second_summary = second.fit(reference)

    assert first_summary.reference_rows == 70
    assert first_summary.selected_components == second_summary.selected_components
    assert first_summary.bic_by_components == second_summary.bic_by_components
    assert first.score(transactions).notna().all()


def test_gmm_rejects_small_reference(transactions):
    detector = GaussianMixtureDetector(max_components=1)

    with pytest.raises(ValueError, match="20 filas"):
        detector.fit(transactions.head(10))


def test_evaluation_reports_minority_class_metrics(transactions):
    labels = transactions["isFraud"]
    scores = labels.astype(float)

    result = evaluate_scores(labels, scores, threshold=0.5, top_k_fraction=0.1)

    assert result["positive_labels"] == 3
    assert result["pr_auc"] == 1.0
    assert result["recall"] == 1.0
    assert "accuracy" not in result
