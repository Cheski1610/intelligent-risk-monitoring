"""Chunked CSV loading for the original PaySim schema."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import pandas as pd

from irml.data.validation import (
    DataValidationError,
    QualityReport,
    REQUIRED_COLUMNS,
    normalize_frame,
    validate_columns,
)

logger = logging.getLogger(__name__)
INTERNAL_COLUMNS = {"_source_row_id"}


@dataclass(slots=True)
class TransactionData:
    frame: pd.DataFrame
    quality: QualityReport
    source_path: Path


def iter_transaction_chunks(
    path: str | Path,
    *,
    chunksize: int = 250_000,
) -> Iterator[TransactionData]:
    """Yield typed chunks while retaining source row IDs and every input row."""
    source = Path(path).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"No existe el archivo de transacciones: {source}")

    try:
        reader = pd.read_csv(
            source,
            dtype="string",
            keep_default_na=False,
            chunksize=chunksize,
            encoding="utf-8-sig",
        )
        first_source_row = 2
        for raw in reader:
            validate_columns(list(raw.columns))
            frame, quality = normalize_frame(raw, first_source_row=first_source_row)
            first_source_row += len(raw)
            yield TransactionData(frame=frame, quality=quality, source_path=source)
    except pd.errors.EmptyDataError as exc:
        raise DataValidationError("El archivo CSV está vacío.") from exc
    except pd.errors.ParserError as exc:
        raise DataValidationError(f"No se pudo interpretar el CSV: {exc}") from exc


def load_transactions(
    path: str | Path,
    *,
    chunksize: int = 250_000,
) -> TransactionData:
    """Load a CSV in chunks and concatenate normalized data for interactive use."""
    source = Path(path).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"No existe el archivo de transacciones: {source}")
    try:
        header = pd.read_csv(source, nrows=0, encoding="utf-8-sig")
    except pd.errors.EmptyDataError as exc:
        raise DataValidationError("El archivo CSV está vacío.") from exc
    validate_columns(list(header.columns))

    chunks: list[pd.DataFrame] = []
    totals: dict[str, dict[str, int]] = {
        "missing_cells": {},
        "invalid_numeric_values": {},
        "invalid_labels": {},
        "unexpected_transaction_types": {},
    }
    rows = 0
    warnings: list[str] = []
    try:
        for item in iter_transaction_chunks(source, chunksize=chunksize):
            chunks.append(item.frame)
            rows += item.quality.rows_processed
            for name in totals:
                for key, value in getattr(item.quality, name).items():
                    totals[name][key] = totals[name].get(key, 0) + value
            warnings.extend(item.quality.warnings)
    except UnicodeDecodeError as exc:
        raise DataValidationError("El archivo debe estar codificado como UTF-8.") from exc

    if not chunks:
        raise DataValidationError("El CSV tiene encabezados, pero no contiene transacciones.")

    frame = pd.concat(chunks, ignore_index=True)
    duplicate_count = int(frame.duplicated(subset=list(REQUIRED_COLUMNS)).sum())
    if duplicate_count:
        warnings.append("Se detectaron filas duplicadas en el archivo completo; no se eliminaron.")
    report = QualityReport(
        rows_processed=rows,
        missing_cells=totals["missing_cells"],
        invalid_numeric_values=totals["invalid_numeric_values"],
        invalid_labels=totals["invalid_labels"],
        unexpected_transaction_types=totals["unexpected_transaction_types"],
        exact_duplicate_rows=duplicate_count,
        warnings=list(dict.fromkeys(warnings)),
    )
    logger.info("Loaded %s transaction rows from %s", rows, source)
    return TransactionData(frame=frame, quality=report, source_path=source)
