from __future__ import annotations

import pandas as pd

from irml.risk_monitoring.aggregation import aggregate_indicators
from irml.risk_monitoring.change_detection import detect_changes
from irml.risk_monitoring.replay import shift_replay_period


def test_hourly_aggregation_uses_expansion_weights(transactions):
    frame = transactions.iloc[:3].copy()
    frame["step"] = [1, 1, 2]
    weights = {1: 10.0, 2: 20.0}

    hourly = aggregate_indicators(frame, granularity="hour", expansion_weights=weights)
    daily = aggregate_indicators(frame, granularity="day", expansion_weights=weights)

    assert hourly.loc[hourly["period"] == 1, "sample_count"].iloc[0] == 2
    assert hourly.loc[hourly["period"] == 1, "estimated_transaction_count"].iloc[0] == 20
    assert daily["sample_count"].iloc[0] == 3
    assert daily["estimated_transaction_count"].iloc[0] == 40


def test_stable_reference_has_no_change_alerts():
    series = pd.DataFrame(
        {
            "period": range(1, 8),
            "end_step": range(1, 8),
            "indicator": [10.0] * 7,
        }
    )

    changes, limit = detect_changes(
        series,
        "indicator",
        last_reference_step=4,
        minimum_persistence=2,
    )

    assert limit.reference_periods == 4
    assert not changes["is_alert"].any()


def test_controlled_persistent_shift_triggers_after_two_periods():
    series = pd.DataFrame(
        {
            "period": range(1, 8),
            "end_step": range(1, 8),
            "indicator": [10.0, 10.0, 10.0, 10.0, 10.0, 25.0, 25.0],
        }
    )

    changes, _ = detect_changes(
        series,
        "indicator",
        last_reference_step=5,
        minimum_persistence=2,
    )

    assert not bool(changes.loc[5, "is_alert"])
    assert bool(changes.loc[6, "is_alert"])
    assert pd.notna(changes.loc[6, "deviation_score"])


def test_replay_period_navigation_clamps_to_available_bounds():
    assert shift_replay_period(4, 1, first_period=1, last_period=5) == 5
    assert shift_replay_period(1, -1, first_period=1, last_period=5) == 1
    assert shift_replay_period(2, 1, first_period=1, last_period=5) == 3
