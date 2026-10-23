"""Schema and row-quality checks for PaySim transactions."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import pandas as pd


REQUIRED_COLUMNS = (
    "step",
    "type",
    "amount",
    "nameOrig",
    "oldbalanceOrg",
    "newbalanceOrig",
    "nameDest",
    "oldbalanceDest",
    "newbalanceDest",
    "isFraud",
    "isFlaggedFraud",
)
NUMERIC_COLUMNS = (
    "step",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "isFraud",
    "isFlaggedFraud",
)
IDENTIFIER_COLUMNS = ("nameOrig", "nameDest")
ALLOWED_TYPES = {"CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"}


class DataValidationError(ValueError):
    """Raised for structural or parsing errors that prevent safe loading."""


@dataclass(slots=True)
class QualityReport:
    rows_processed: int
    missing_cells: dict[str, int] = field(default_factory=dict)
    invalid_numeric_values: dict[str, int] = field(default_factory=dict)
    invalid_labels: dict[str, int] = field(default_factory=dict)
    unexpected_transaction_types: dict[str, int] = field(default_factory=dict)
    exact_duplicate_rows: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def has_quality_issues(self) -> bool:
        return bool(
            self.missing_cells
            or self.invalid_numeric_values
            or self.invalid_labels
            or self.unexpected_transaction_types
            or self.exact_duplicate_rows
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["has_quality_issues"] = self.has_quality_issues
        return result


def validate_columns(columns: list[str] | tuple[str, ...]) -> list[str]:
    missing = [column for column in REQUIRED_COLUMNS if column not in columns]
    if missing:
        raise DataValidationError(f"Faltan columnas obligatorias: {', '.join(missing)}")
    extras = [column for column in columns if column not in REQUIRED_COLUMNS and column != "_source_row_id"]
    return extras


def normalize_frame(
    raw: pd.DataFrame,
    *,
    first_source_row: int = 2,
) -> tuple[pd.DataFrame, QualityReport]:
    """Validate structure, retain every row, and convert invalid values to NA."""
    extra_columns = validate_columns(list(raw.columns))
    missing_cells: dict[str, int] = {}
    invalid_numeric: dict[str, int] = {}
    invalid_labels: dict[str, int] = {}

    for column in REQUIRED_COLUMNS:
        empty = raw[column].isna() | raw[column].astype("string").str.strip().eq("")
        count = int(empty.sum())
        if count:
            missing_cells[column] = count

    result = raw.copy(deep=False)
    for column in NUMERIC_COLUMNS:
        original = raw[column].astype("string")
        values = pd.to_numeric(original, errors="coerce")
        invalid = original.notna() & original.str.strip().ne("") & values.isna()
        if column == "step":
            fractional = values.notna() & values.mod(1).ne(0)
            if fractional.any():
                invalid_numeric[column] = int(invalid.sum() + fractional.sum())
                values = values.mask(fractional)
            elif invalid.any():
                invalid_numeric[column] = int(invalid.sum())
            result[column] = values.astype("Int64")
        else:
            if invalid.any():
                invalid_numeric[column] = int(invalid.sum())
            result[column] = values.astype("Float64")

    for column in IDENTIFIER_COLUMNS:
        result[column] = raw[column].astype("string")
    result["type"] = raw["type"].astype("string")

    for column in ("isFraud", "isFlaggedFraud"):
        invalid = ~result[column].isin([0, 1]) & result[column].notna()
        if invalid.any():
            invalid_labels[column] = int(invalid.sum())

    if "_source_row_id" in raw.columns:
        result["_source_row_id"] = raw["_source_row_id"].astype("string")
    else:
        result["_source_row_id"] = pd.Series(
            range(first_source_row, first_source_row + len(raw)),
            index=raw.index,
            dtype="string",
        )

    type_counts = raw["type"].value_counts(dropna=False)
    unexpected_types = {
        str(kind): int(count)
        for kind, count in type_counts.items()
        if pd.isna(kind) or kind not in ALLOWED_TYPES
    }
    duplicate_count = int(raw.duplicated(subset=list(REQUIRED_COLUMNS)).sum())
    warnings: list[str] = []
    if extra_columns:
        warnings.append(f"Se conservaron columnas adicionales: {', '.join(extra_columns)}")
    if duplicate_count:
        warnings.append("Se detectaron filas duplicadas; no se eliminaron.")
    if invalid_numeric or invalid_labels or missing_cells:
        warnings.append("Hay valores con problemas de calidad; las filas se conservaron.")

    report = QualityReport(
        rows_processed=len(raw),
        missing_cells=missing_cells,
        invalid_numeric_values=invalid_numeric,
        invalid_labels=invalid_labels,
        unexpected_transaction_types=unexpected_types,
        exact_duplicate_rows=duplicate_count,
        warnings=warnings,
    )
    return result, report
