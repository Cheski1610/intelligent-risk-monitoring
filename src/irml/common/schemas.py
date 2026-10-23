"""Typed alert contract shared by the three applications."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AlertSeverity(StrEnum):
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(StrEnum):
    NEW = "new"
    IN_REVIEW = "in_review"
    CLOSED = "closed"


class Alert(BaseModel):
    """A review signal, not a finding or a confirmed fraud decision."""

    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    alert_id: str = Field(default_factory=lambda: str(uuid4()))
    source_tool: Literal["anomaly_detection", "risk_monitoring"]
    event_step: int | None = None
    transaction_id: str | None = None
    risk_category: str
    score_type: Literal["anomaly_score", "review_priority", "fraud_probability"]
    score_value: float
    severity: AlertSeverity
    reason_codes: list[str] = Field(default_factory=list)
    observed_values: dict[str, Any] = Field(default_factory=dict)
    reference_values: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    status: AlertStatus = AlertStatus.NEW
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("score_value")
    @classmethod
    def validate_probability_range(cls, value: float, info: Any) -> float:
        if info.data.get("score_type") == "fraud_probability" and not 0 <= value <= 1:
            raise ValueError("fraud_probability must be between 0 and 1")
        return value
