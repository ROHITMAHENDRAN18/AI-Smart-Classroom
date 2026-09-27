"""Temporal smoothing for student attention states.

This module is independent of camera, model, persistence, and dashboard code.
It smooths already-computed attention observations, keeping bounded history
for each tracking ID.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
import math
from typing import Deque, Optional


@dataclass
class SmoothedAttentionResult:
    """Temporally smoothed state, score, and evidence coverage."""

    attention_state: str
    attention_score: Optional[float]
    confidence: float
    sample_count: int
    stable: bool


class AttentionTemporalSmoother:
    """Maintain short, independent attention histories for tracked students."""

    VALID_STATES = {
        "ATTENTIVE",
        "PARTIAL",
        "NOT ATTENTIVE",
        "UNKNOWN",
    }

    def __init__(
        self,
        window_size: int = 5,
        minimum_samples: int = 3,
        state_threshold: float = 0.60,
        score_decay: float = 0.80,
    ):
        if type(window_size) is not int or window_size <= 0:
            raise ValueError("window_size must be a positive integer.")
        if type(minimum_samples) is not int or minimum_samples <= 0:
            raise ValueError("minimum_samples must be a positive integer.")
        if minimum_samples > window_size:
            raise ValueError("minimum_samples cannot exceed window_size.")

        state_threshold = self._finite_number(state_threshold, "state_threshold")
        score_decay = self._finite_number(score_decay, "score_decay")
        if not 0.0 < state_threshold <= 1.0:
            raise ValueError("state_threshold must be greater than 0 and at most 1.")
        if not 0.0 < score_decay <= 1.0:
            raise ValueError("score_decay must be greater than 0 and at most 1.")

        self.window_size = window_size
        self.minimum_samples = minimum_samples
        self.state_threshold = state_threshold
        self.score_decay = score_decay
        self._history: dict[int, Deque[tuple[str, Optional[float], float]]] = {}

    @staticmethod
    def _finite_number(value: float, name: str) -> float:
        try:
            normalized = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{name} must be a finite number.") from error
        if not math.isfinite(normalized):
            raise ValueError(f"{name} must be a finite number.")
        return normalized

    @staticmethod
    def _normalize_track_id(track_id: int) -> int:
        if isinstance(track_id, bool):
            raise ValueError("track_id must be an integer identifier.")
        try:
            return int(track_id)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("track_id must be an integer identifier.") from error

    @classmethod
    def _normalize_state(cls, state: Optional[str]) -> str:
        if state is None:
            return "UNKNOWN"
        normalized = str(state).strip().upper()
        if normalized not in cls.VALID_STATES:
            raise ValueError(f"Unsupported attention state: {state!r}")
        return normalized

    @classmethod
    def _normalize_score(cls, score: Optional[float]) -> Optional[float]:
        if score is None:
            return None
        return max(0.0, min(1.0, cls._finite_number(score, "attention_score")))

    @classmethod
    def _normalize_confidence(cls, confidence: float) -> float:
        return max(0.0, min(1.0, cls._finite_number(confidence, "confidence")))

    def _get_history(self, track_id: int) -> Deque[tuple[str, Optional[float], float]]:
        if track_id not in self._history:
            self._history[track_id] = deque(maxlen=self.window_size)
        return self._history[track_id]

    def update(
        self,
        track_id: int,
        attention_state: Optional[str],
        attention_score: Optional[float] = None,
        confidence: float = 0.0,
    ) -> SmoothedAttentionResult:
        """Add a known observation; UNKNOWN leaves existing history untouched."""
        track_id = self._normalize_track_id(track_id)
        state = self._normalize_state(attention_state)
        score = self._normalize_score(attention_score)
        normalized_confidence = self._normalize_confidence(confidence)
        history = self._get_history(track_id)

        if state != "UNKNOWN":
            history.append((state, score, normalized_confidence))

        return self._result_for_history(history)

    def _result_for_history(
        self,
        history: Deque[tuple[str, Optional[float], float]],
    ) -> SmoothedAttentionResult:
        if not history:
            return SmoothedAttentionResult(
                attention_state="UNKNOWN",
                attention_score=None,
                confidence=0.0,
                sample_count=0,
                stable=False,
            )

        state_counts = Counter(item[0] for item in history)
        dominant_state, dominant_count = state_counts.most_common(1)[0]
        sample_count = len(history)
        dominance = dominant_count / sample_count
        stable = (
            sample_count >= self.minimum_samples
            and dominance >= self.state_threshold
        )
        attention_state = dominant_state if stable else "UNKNOWN"

        scores = [
            (score, confidence)
            for _, score, confidence in reversed(history)
            if score is not None
        ]
        attention_score = self._weighted_score(scores)
        average_confidence = sum(item[2] for item in history) / sample_count
        temporal_confidence = average_confidence * dominance
        if not stable:
            temporal_confidence *= 0.5

        return SmoothedAttentionResult(
            attention_state=attention_state,
            attention_score=attention_score,
            confidence=round(temporal_confidence, 4),
            sample_count=sample_count,
            stable=stable,
        )

    def _weighted_score(
        self,
        scores: list[tuple[float, float]],
    ) -> Optional[float]:
        if not scores:
            return None

        total_weight = 0.0
        weighted_score = 0.0
        for index, (score, _) in enumerate(scores):
            weight = self.score_decay ** index
            weighted_score += score * weight
            total_weight += weight

        if total_weight == 0.0:
            return None
        return round(weighted_score / total_weight, 4)

    def clear_track(self, track_id: int) -> None:
        """Remove history for a single tracking ID."""
        self._history.pop(self._normalize_track_id(track_id), None)

    def clear_all(self) -> None:
        """Remove history for every track."""
        self._history.clear()

    def retain_tracks(self, active_track_ids) -> int:
        """Discard histories for tracks absent from the current tracker output."""
        active_tracks = {
            self._normalize_track_id(track_id)
            for track_id in active_track_ids
        }
        stale_tracks = self._history.keys() - active_tracks
        for track_id in stale_tracks:
            del self._history[track_id]
        return len(stale_tracks)

    def get_history(
        self,
        track_id: int,
    ) -> list[tuple[str, Optional[float], float]]:
        """Return a copy of the observations for one track."""
        history = self._history.get(self._normalize_track_id(track_id))
        return list(history) if history is not None else []
