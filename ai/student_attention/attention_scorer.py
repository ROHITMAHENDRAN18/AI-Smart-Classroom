"""Convert smoothed attention signals into student-level scores.

This module is independent of camera, model, persistence, and dashboard code.
Scores are presented as percentages; attention states are emitted only when the
input temporal observation is stable.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional


@dataclass
class StudentAttentionResult:
    """Student-level score derived from a temporal attention observation."""

    student_id: str
    attention_score: Optional[float]
    attention_state: str
    stable: bool
    temporal_confidence: float


class StudentAttentionScorer:
    """Map a normalized smoothed score to a percentage and state."""

    def __init__(
        self,
        attentive_threshold: float = 0.70,
        partial_threshold: float = 0.45,
    ):
        attentive_threshold = self._finite_number(
            attentive_threshold,
            "attentive_threshold",
        )
        partial_threshold = self._finite_number(
            partial_threshold,
            "partial_threshold",
        )
        if not 0.0 <= partial_threshold < attentive_threshold <= 1.0:
            raise ValueError(
                "Thresholds must satisfy 0 <= partial_threshold "
                "< attentive_threshold <= 1."
            )

        self.attentive_threshold = attentive_threshold
        self.partial_threshold = partial_threshold

    @staticmethod
    def _finite_number(value: float, name: str) -> float:
        try:
            normalized = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{name} must be a finite number.") from error
        if not math.isfinite(normalized):
            raise ValueError(f"{name} must be a finite number.")
        return normalized

    @classmethod
    def _normalize_student_id(cls, student_id: str) -> str:
        if student_id is None:
            raise ValueError("student_id cannot be None.")
        normalized = str(student_id).strip()
        if not normalized:
            raise ValueError("student_id cannot be empty.")
        return normalized

    @classmethod
    def _normalize_score(cls, attention_score: Optional[float]) -> Optional[float]:
        if attention_score is None:
            return None
        score = cls._finite_number(attention_score, "attention_score")
        return max(0.0, min(1.0, score))

    @classmethod
    def _normalize_confidence(cls, temporal_confidence: float) -> float:
        confidence = cls._finite_number(temporal_confidence, "temporal_confidence")
        return max(0.0, min(1.0, confidence))

    def calculate_state(self, attention_score: Optional[float]) -> str:
        """Classify a normalized 0-1 score using configured thresholds."""
        score = self._normalize_score(attention_score)
        if score is None:
            return "UNKNOWN"
        if score >= self.attentive_threshold:
            return "ATTENTIVE"
        if score >= self.partial_threshold:
            return "PARTIAL"
        return "NOT ATTENTIVE"

    def calculate_score_percentage(
        self,
        attention_score: Optional[float],
    ) -> Optional[float]:
        """Convert a normalized 0-1 score to a 0-100 percentage."""
        score = self._normalize_score(attention_score)
        if score is None:
            return None
        return round(score * 100.0, 2)

    def calculate(
        self,
        student_id: str,
        attention_score: Optional[float],
        stable: bool,
        temporal_confidence: float,
    ) -> StudentAttentionResult:
        """Build a score result, withholding a categorical state until stable."""
        normalized_student_id = self._normalize_student_id(student_id)
        score = self._normalize_score(attention_score)
        confidence = self._normalize_confidence(temporal_confidence)
        if not isinstance(stable, bool):
            raise ValueError("stable must be a boolean.")

        if score is None:
            return StudentAttentionResult(
                student_id=normalized_student_id,
                attention_score=None,
                attention_state="UNKNOWN",
                stable=False,
                temporal_confidence=confidence,
            )

        percentage = round(score * 100.0, 2)
        state = self.calculate_state(score) if stable else "UNKNOWN"
        return StudentAttentionResult(
            student_id=normalized_student_id,
            attention_score=percentage,
            attention_state=state,
            stable=stable,
            temporal_confidence=confidence,
        )
