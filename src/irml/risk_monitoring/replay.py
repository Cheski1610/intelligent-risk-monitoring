"""Bounded time-step navigation for the simulated risk-monitoring replay."""
from __future__ import annotations


def shift_replay_period(
    current_period: int,
    offset: int,
    *,
    first_period: int,
    last_period: int,
) -> int:
    """Move within replay bounds, clamping at either end."""
    if first_period > last_period:
        raise ValueError("first_period debe ser menor o igual que last_period.")
    return max(first_period, min(last_period, current_period + offset))
