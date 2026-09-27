"""Standalone weighted fusion of classroom attention signals.

This module does not access cameras, models, persistence, dashboards, or the
live classroom pipeline. Missing signals are excluded instead of being treated
as negative or neutral observations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Dict, Optional


@dataclass
class AttentionFusionResult:
    """Student-level result and the evidence used to calculate it.

    ``confidence`` describes configured signal-weight coverage, not calibrated
    model certainty. An unavailable result has no numeric attention score.
    """

    attention_state: str
    attention_score: Optional[float]
    confidence: float
    eye_state: str
    head_pose: str
    emotion: str
    phone_detected: Optional[bool]
    hand_raised: Optional[bool]
    signal_scores: Dict[str, float] = field(default_factory=dict)
    signal_weights: Dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)


class AttentionFusionEngine:
    """Combine detector states into a weighted, explainable attention score."""

    VALID_EYE_STATES = {"OPEN", "CLOSED", "PARTIAL", "UNKNOWN"}
    VALID_HEAD_POSES = {"FRONT", "LEFT", "RIGHT", "UP", "DOWN", "UNKNOWN"}
    VALID_EMOTIONS = {"HAPPY", "SAD", "ANGRY", "SURPRISED", "NEUTRAL", "UNKNOWN"}

    def __init__(
        self,
        eye_weight: float = 0.30,
        head_pose_weight: float = 0.30,
        emotion_weight: float = 0.10,
        phone_weight: float = 0.20,
        hand_weight: float = 0.10,
    ):
        raw_weights = {
            "eye": eye_weight,
            "head_pose": head_pose_weight,
            "emotion": emotion_weight,
            "phone": phone_weight,
            "hand": hand_weight,
        }

        try:
            weights = {name: float(value) for name, value in raw_weights.items()}
        except (TypeError, ValueError) as error:
            raise ValueError("Fusion weights must be finite non-negative numbers.") from error

        if any(not math.isfinite(value) or value < 0.0 for value in weights.values()):
            raise ValueError("Fusion weights must be finite non-negative numbers.")

        total_weight = sum(weights.values())
        if total_weight <= 0.0:
            raise ValueError("At least one fusion weight must be positive.")

        self.weights = {name: value / total_weight for name, value in weights.items()}

    @staticmethod
    def _normalize_state(value: Optional[str], valid_values: set[str], signal_name: str) -> str:
        if value is None:
            return "UNKNOWN"

        normalized = str(value).strip().upper()
        if normalized not in valid_values:
            raise ValueError(f"Unsupported {signal_name} value: {value!r}")
        return normalized

    @staticmethod
    def _normalize_boolean(value: Optional[bool], signal_name: str) -> Optional[bool]:
        if value is None:
            return None
        if not isinstance(value, bool):
            raise ValueError(f"{signal_name} must be True, False, or None.")
        return value

    @staticmethod
    def _eye_score(eye_state: str) -> Optional[float]:
        return {
            "OPEN": 1.0,
            "PARTIAL": 0.5,
            "CLOSED": 0.0,
            "UNKNOWN": None,
        }[eye_state]

    @staticmethod
    def _head_pose_score(head_pose: str) -> Optional[float]:
        return {
            "FRONT": 1.0,
            "LEFT": 0.35,
            "RIGHT": 0.35,
            "UP": 0.20,
            "DOWN": 0.20,
            "UNKNOWN": None,
        }[head_pose]

    @staticmethod
    def _emotion_score(emotion: str) -> Optional[float]:
        return {
            "HAPPY": 1.0,
            "NEUTRAL": 1.0,
            "SURPRISED": 0.7,
            "SAD": 0.5,
            "ANGRY": 0.5,
            "UNKNOWN": None,
        }[emotion]

    @staticmethod
    def _boolean_score(value: Optional[bool], positive_score: float, negative_score: float) -> Optional[float]:
        if value is None:
            return None
        return positive_score if value else negative_score

    def fuse(
        self,
        eye_state: Optional[str] = "UNKNOWN",
        head_pose: Optional[str] = "UNKNOWN",
        emotion: Optional[str] = "UNKNOWN",
        phone_detected: Optional[bool] = None,
        hand_raised: Optional[bool] = None,
    ) -> AttentionFusionResult:
        """Fuse any available inputs; absent/unknown signals do not affect score."""
        eye_state = self._normalize_state(eye_state, self.VALID_EYE_STATES, "eye state")
        head_pose = self._normalize_state(head_pose, self.VALID_HEAD_POSES, "head pose")
        emotion = self._normalize_state(emotion, self.VALID_EMOTIONS, "emotion")
        phone_detected = self._normalize_boolean(phone_detected, "phone_detected")
        hand_raised = self._normalize_boolean(hand_raised, "hand_raised")

        observed_scores = {
            "eye": self._eye_score(eye_state),
            "head_pose": self._head_pose_score(head_pose),
            "emotion": self._emotion_score(emotion),
            "phone": self._boolean_score(phone_detected, positive_score=0.0, negative_score=1.0),
            "hand": self._boolean_score(hand_raised, positive_score=1.0, negative_score=0.8),
        }
        signal_scores = {
            name: score for name, score in observed_scores.items() if score is not None
        }
        available_weight = sum(self.weights[name] for name in signal_scores)

        reasons = []
        if eye_state == "CLOSED":
            reasons.append("Eyes are closed.")
        if head_pose in {"LEFT", "RIGHT", "UP", "DOWN"}:
            reasons.append("Head is not facing forward.")
        if phone_detected is True:
            reasons.append("Phone detected.")
        if hand_raised is True:
            reasons.append("Hand raised.")

        if available_weight <= 0.0:
            return AttentionFusionResult(
                attention_state="UNKNOWN",
                attention_score=None,
                confidence=0.0,
                eye_state=eye_state,
                head_pose=head_pose,
                emotion=emotion,
                phone_detected=phone_detected,
                hand_raised=hand_raised,
                reasons=reasons,
            )

        weighted_score = sum(
            signal_scores[name] * self.weights[name] for name in signal_scores
        )
        attention_score = weighted_score / available_weight

        if attention_score >= 0.70:
            attention_state = "ATTENTIVE"
        elif attention_score >= 0.45:
            attention_state = "PARTIAL"
        else:
            attention_state = "NOT ATTENTIVE"

        return AttentionFusionResult(
            attention_state=attention_state,
            attention_score=round(attention_score, 4),
            confidence=round(available_weight, 4),
            eye_state=eye_state,
            head_pose=head_pose,
            emotion=emotion,
            phone_detected=phone_detected,
            hand_raised=hand_raised,
            signal_scores={name: round(score, 4) for name, score in signal_scores.items()},
            signal_weights={name: round(self.weights[name], 4) for name in signal_scores},
            reasons=reasons,
        )