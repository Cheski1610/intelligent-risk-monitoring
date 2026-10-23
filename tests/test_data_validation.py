from __future__ import annotations

import pandas as pd
import pytest

from irml.data.loader import load_transactions
from irml.data.validation import DataValidationError, REQUIRED_COLUMNS, normalize_frame


def test_valid_csv_loads_and_gets_stable_row_ids(paysim_csv):
    loaded = load_transactions(paysim_csv, chunksize=17)

    assert len(loaded.frame) == 100
    assert loaded.frame["_source_row_id"].iloc[0] == "2"
    assert loaded.frame["_source_row_id"].iloc[-1] == "101"
    assert not loaded.quality.has_quality_issues


def test_missing_columns_are_a_format_error(transactions):
    with pytest.raises(DataValidationError, match="Faltan columnas"):
        normalize_frame(transactions.drop(columns=["amount"]))


def test_invalid_values_are_reported_and_rows_are_preserved(transactions):
    # Model raw CSV input so pandas 3 permits injecting malformed text into
    # columns that are numeric after normalization.
    raw = transactions.astype(
        {
            "amount": "object",
            "step": "object",
            "isFraud": "object",
            "type": "object",
            "nameOrig": "object",
        }
    )
    raw.loc[0, "amount"] = "not-a-number"
    raw.loc[1, "step"] = "2.5"
    raw.loc[2, "isFraud"] = 4
    raw.loc[3, "type"] = "UNKNOWN"
    raw.loc[4, "nameOrig"] = ""

    normalized, report = normalize_frame(raw)

    assert len(normalized) == len(raw)
    assert report.invalid_numeric_values["amount"] == 1
    assert report.invalid_numeric_values["step"] == 1
    assert report.invalid_labels["isFraud"] == 1
    assert report.unexpected_transaction_types["UNKNOWN"] == 1
    assert report.missing_cells["nameOrig"] == 1


def test_duplicates_are_reported_without_dropping_rows(transactions):
    raw = pd.concat([transactions, transactions.iloc[[0]]], ignore_index=True)

    normalized, report = normalize_frame(raw)

    assert len(normalized) == 101
    assert report.exact_duplicate_rows == 1


def test_empty_file_is_a_format_error(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")

    with pytest.raises(DataValidationError, match="vacío"):
        load_transactions(path)


def test_source_schema_has_expected_original_columns():
    assert len(REQUIRED_COLUMNS) == 11
    assert "isFraud" in REQUIRED_COLUMNS
    assert "_source_row_id" not in REQUIRED_COLUMNS
