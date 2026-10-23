"""Profile PaySim in one pass and create a deterministic, ordered demo sample."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

EXPECTED_COLUMNS = (
    "step", "type", "amount", "nameOrig", "oldbalanceOrg", "newbalanceOrig",
    "nameDest", "oldbalanceDest", "newbalanceDest", "isFraud", "isFlaggedFraud",
)
SAMPLE_COLUMNS = EXPECTED_COLUMNS + ("_source_row_id",)
NUMERIC_COLUMNS = (
    "step", "amount", "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest",
    "newbalanceDest", "isFraud", "isFlaggedFraud",
)
SPLITS = ((1, 323, "reference"), (324, 378, "validation"), (379, 743, "test"))


def quantile(values: list[float], proportion: float) -> float | None:
    if not values:
        return None
    values.sort()
    index = (len(values) - 1) * proportion
    lower, upper = math.floor(index), math.ceil(index)
    return values[lower] if lower == upper else values[lower] * (upper - index) + values[upper] * (index - lower)


def profile(source: Path, sample_path: Path, report_path: Path, rate: float, seed: int) -> dict:
    if not 0 < rate <= 1:
        raise ValueError("sample rate must be in (0, 1]")
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    count = sample_count = duplicate_count = 0
    missing, invalid = Counter(), Counter()
    types, frauds, flags = Counter(), Counter(), Counter()
    fraud_by_type = defaultdict(Counter)
    rows_by_step, fraud_by_step = Counter(), Counter()
    seen_hashes: set[bytes] = set()
    origins: set[str] = set()
    destinations: set[str] = set()
    amounts: list[float] = []
    amount_sum, amount_min, amount_max = 0.0, math.inf, -math.inf
    rng, sample_rng = random.Random(seed + 1), random.Random(seed)
    previous_step, order_regressions = None, 0
    origin_mismatches = destination_mismatches = 0

    with source.open("r", encoding="utf-8-sig", newline="") as source_file:
        reader = csv.DictReader(source_file)
        if tuple(reader.fieldnames or ()) != EXPECTED_COLUMNS:
            raise ValueError(f"Unexpected schema: {reader.fieldnames}")
        with sample_path.open("w", encoding="utf-8", newline="") as sample_file:
            writer = csv.DictWriter(sample_file, fieldnames=EXPECTED_COLUMNS)
            writer.writeheader()
            for row in reader:
                count += 1
                for column in EXPECTED_COLUMNS:
                    if row[column] is None or not row[column].strip():
                        missing[column] += 1
                parsed = {}
                for column in NUMERIC_COLUMNS:
                    try:
                        number = float(row[column])
                        if not math.isfinite(number):
                            raise ValueError
                        parsed[column] = number
                    except (TypeError, ValueError):
                        invalid[column] += 1
                step = None
                if "step" in parsed and parsed["step"].is_integer():
                    step = int(parsed["step"])
                    rows_by_step[step] += 1
                    if previous_step is not None and step < previous_step:
                        order_regressions += 1
                    previous_step = step

                kind = row["type"]
                types[kind] += 1
                try:
                    label = int(row["isFraud"])
                    frauds[label] += 1
                    fraud_by_type[kind][label] += 1
                    if step is not None:
                        fraud_by_step[step] += label == 1
                except (TypeError, ValueError):
                    pass
                try:
                    flags[int(row["isFlaggedFraud"])] += 1
                except (TypeError, ValueError):
                    pass

                origins.add(row["nameOrig"])
                destinations.add(row["nameDest"])
                if "amount" in parsed:
                    amount = parsed["amount"]
                    amount_sum += amount
                    amount_min, amount_max = min(amount_min, amount), max(amount_max, amount)
                    if len(amounts) < 100_000:
                        amounts.append(amount)
                    else:
                        index = rng.randrange(count)
                        if index < len(amounts):
                            amounts[index] = amount
                if all(name in parsed for name in ("amount", "oldbalanceOrg", "newbalanceOrig")):
                    origin_mismatches += not math.isclose(
                        parsed["oldbalanceOrg"] - parsed["newbalanceOrig"],
                        parsed["amount"], rel_tol=0, abs_tol=0.01,
                    )
                if all(name in parsed for name in ("amount", "oldbalanceDest", "newbalanceDest")):
                    destination_mismatches += not math.isclose(
                        parsed["newbalanceDest"] - parsed["oldbalanceDest"],
                        parsed["amount"], rel_tol=0, abs_tol=0.01,
                    )

                digest = hashlib.blake2b(
                    "\x1f".join(row[column] for column in EXPECTED_COLUMNS).encode("utf-8"),
                    digest_size=16,
                ).digest()
                if digest in seen_hashes:
                    duplicate_count += 1
                else:
                    seen_hashes.add(digest)
                if sample_rng.random() < rate:
                    writer.writerow(row)
                    sample_count += 1

    if count == 0:
        raise ValueError("CSV has a header but no transaction rows")
    steps = sorted(rows_by_step)
    if order_regressions:
        raise ValueError("Source rows are not ordered by step; refusing to create an ordered demo sample")

    # Stratify by step so sparse hours remain visible in replay. Inclusion is
    # independent of labels; weights are recorded for volume estimates.
    selected_positions: set[int] = set()
    sample_rows_by_step: dict[int, int] = {}
    sample_rng = random.Random(seed)
    offset = 0
    for step in steps:
        source_count = rows_by_step[step]
        quota = min(source_count, max(1, math.ceil(rate * source_count)))
        selected_positions.update(offset + index for index in sample_rng.sample(range(source_count), quota))
        sample_rows_by_step[step] = quota
        offset += source_count
    if offset != count:
        raise ValueError("Rows with invalid step values prevent a complete stratified sample")

    sample_count = 0
    with source.open("r", encoding="utf-8-sig", newline="") as source_file:
        reader = csv.DictReader(source_file)
        with sample_path.open("w", encoding="utf-8", newline="") as sample_file:
            writer = csv.DictWriter(sample_file, fieldnames=SAMPLE_COLUMNS)
            writer.writeheader()
            for row_index, row in enumerate(reader):
                if row_index in selected_positions:
                    writer.writerow({**row, "_source_row_id": row_index + 2})
                    sample_count += 1

    sample_steps: set[int] = set()
    with sample_path.open("r", encoding="utf-8", newline="") as sample_file:
        for row in csv.DictReader(sample_file):
            sample_steps.add(int(row["step"]))
    split_counts = {
        name: sum(rows_by_step.get(step, 0) for step in range(start, end + 1))
        for start, end, name in SPLITS
    }
    result = {
        "source": source.name,
        "source_bytes": source.stat().st_size,
        "rows": count,
        "columns": list(EXPECTED_COLUMNS),
        "step_min": min(steps),
        "step_max": max(steps),
        "step_count": len(steps),
        "step_order_regressions": order_regressions,
        "rows_by_step_min": min(rows_by_step.values()),
        "rows_by_step_max": max(rows_by_step.values()),
        "transaction_types": dict(types),
        "fraud_labels": dict(frauds),
        "flag_labels": dict(flags),
        "fraud_by_type": {key: dict(value) for key, value in fraud_by_type.items()},
        "missing_cells": dict(missing),
        "invalid_numeric_cells": dict(invalid),
        "exact_duplicate_rows": duplicate_count,
        "unique_origins": len(origins),
        "unique_destinations": len(destinations),
        "amount_min": amount_min,
        "amount_max": amount_max,
        "amount_mean": amount_sum / count,
        "amount_quantile_reservoir_size": len(amounts),
        "amount_p50_estimate": quantile(amounts, 0.50),
        "amount_p95_estimate": quantile(amounts, 0.95),
        "amount_p99_estimate": quantile(amounts, 0.99),
        "origin_balance_mismatches": origin_mismatches,
        "destination_balance_mismatches": destination_mismatches,
        "sample": {
            "path": sample_path.as_posix(),
            "rows": sample_count,
            "target_rate": rate,
            "realized_rate": sample_count / count,
            "seed": seed,
            "step_coverage": len(sample_steps),
            "sampling_uses_labels": False,
            "preserves_source_order": True,
            "method": "uniform random sample per step with at least one row per step",
            "step_expansion_weights": {
                str(step): rows_by_step[step] / sample_rows_by_step[step]
                for step in steps
            },
        },
        "temporal_splits": {
            f"{name}_{start}_{end}": split_counts[name]
            for start, end, name in SPLITS
        },
    }
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    step_path = report_path.parent / "paysim_profile_by_step.csv"
    with step_path.open("w", encoding="utf-8", newline="") as step_file:
        writer = csv.writer(step_file)
        writer.writerow(("step", "transaction_count", "sample_count", "expansion_weight", "fraud_label_count"))
        for step in steps:
            writer.writerow((
                step,
                rows_by_step[step],
                sample_rows_by_step[step],
                f"{rows_by_step[step] / sample_rows_by_step[step]:.6f}",
                fraud_by_step[step],
            ))
    print(f"Processed {count:,} rows; sample contains {sample_count:,} rows.")
    print(f"Profile: {report_path}; sample: {sample_path}; step series: {step_path}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("PS_20174392719_1491204439457_log.csv"))
    parser.add_argument("--sample", type=Path, default=Path("data/samples/paysim_demo.csv"))
    parser.add_argument("--report", type=Path, default=Path("reports/paysim_profile.json"))
    parser.add_argument("--sample-rate", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=20261021)
    args = parser.parse_args()
    profile(args.source, args.sample, args.report, args.sample_rate, args.seed)


if __name__ == "__main__":
    main()
