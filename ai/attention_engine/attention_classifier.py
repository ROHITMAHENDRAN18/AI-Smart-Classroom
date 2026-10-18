"""Conservative temporal classification of observable classroom behavior.

States describe visible posture and motion cues. They are not claims about a
student's mental attention or intent. Talking remains UNKNOWN unless a caller
provides measured mouth motion across frames.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
import math

VALID_STATES = {
    "LISTENING",
    "SLEEPING",
    "POSSIBLY_TALKING",
    "LOOKING_AWAY",
    "UNKNOWN",
}
def classify_attention_observation(
    *,
    eye_state: str | None,
    head_pose: str | None,
    mouth_motion: bool | None = None,
) -> dict[str, object]:
    """Classify one observation and explain missing or weak evidence.

    ``mouth_motion`` remains accepted for API compatibility but is not used:
    this frame pipeline does not provide temporal mouth-motion evidence.
    """
    eyes = str(eye_state or "UNKNOWN").strip().upper()
    pose = str(head_pose or "UNKNOWN").strip().upper()
    if eyes not in {"OPEN", "CLOSED", "PARTIAL", "UNKNOWN"}:
        eyes = "UNKNOWN"
    if pose not in {"FRONT", "LEFT", "RIGHT", "UP", "DOWN", "UNKNOWN"}:
        pose = "UNKNOWN"

    reasons = []
    if eyes == "UNKNOWN":
        reasons.append("EYE_SIGNAL_UNAVAILABLE")
    if pose == "UNKNOWN":
        reasons.append("HEAD_POSE_UNAVAILABLE")

    if eyes == "CLOSED" and pose in {"LEFT", "RIGHT", "UP"}:
        state = "UNKNOWN"
        reasons.append("CONFLICTING_SIGNALS")
    elif pose == "DOWN" or eyes == "CLOSED":
        state = "SLEEPING"
    elif pose in {"LEFT", "RIGHT", "UP"}:
        state = "LOOKING_AWAY"
    elif pose == "FRONT" and eyes == "OPEN":
        state = "LISTENING"
    else:
        state = "UNKNOWN"
        if not reasons:
            reasons.append("LOW_SIGNAL_QUALITY")

    return {"attention_state": state, "diagnostic_reasons": reasons}


def classify_attention_state(
    *,
    eye_state: str | None,
    head_pose: str | None,
    mouth_motion: bool | None = None,
) -> str:
    """Classify one observation from available eye, pose, and mouth signals."""
    return classify_attention_observation(
        eye_state=eye_state,
        head_pose=head_pose,
        mouth_motion=mouth_motion,
    )["attention_state"]


@dataclass
class _TrackEvidence:
    state: str = "UNKNOWN"
    count: int = 0
    first_seen: datetime | None = None
    last_seen: datetime | None = None


class TemporalAttentionClassifier:
    """Require repeated, sustained evidence independently for each subject key."""

    def __init__(self, minimum_samples: int = 3, minimum_duration_seconds: float = 4.0):
        if type(minimum_samples) is not int or minimum_samples < 2:
            raise ValueError("minimum_samples must be an integer of at least 2")
        try:
            minimum_duration_seconds = float(minimum_duration_seconds)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "minimum_duration_seconds must be finite and non-negative"
            ) from error
        if not math.isfinite(minimum_duration_seconds) or minimum_duration_seconds < 0:
            raise ValueError("minimum_duration_seconds must be finite and non-negative")
        self.minimum_samples = minimum_samples
        self.minimum_duration_seconds = float(minimum_duration_seconds)
        self._evidence: dict[tuple[str, str], _TrackEvidence] = defaultdict(
            _TrackEvidence
        )

    def update(
        self,
        session_id: str,
        student_id: str,
        observation: str,
        observed_at: datetime,
    ) -> dict[str, object]:
        key = (str(session_id), str(student_id))
        now = observed_at

        evidence = self._evidence.get(key)
        if observation not in VALID_STATES or observation == "UNKNOWN":
            if evidence is None:
                return {
                    "attention_state": "UNKNOWN",
                    "stable": False,
                    "sample_count": 0,
                }

            gap = (now - evidence.last_seen).total_seconds()
            if gap < 0 or gap > 10.0:
                self._evidence.pop(key, None)
                return {
                    "attention_state": "UNKNOWN",
                    "stable": False,
                    "sample_count": 0,
                }

            # A brief missing signal is not positive evidence, but it also
            # should not erase valid samples collected for the same student.
            return {
                "attention_state": "UNKNOWN",
                "stable": False,
                "sample_count": evidence.count,
            }

        if evidence is None:
            evidence = self._evidence.setdefault(key, _TrackEvidence())

        if evidence.state != observation or (
            evidence.last_seen is not None
            and (
                (now - evidence.last_seen).total_seconds() < 0
                or (now - evidence.last_seen).total_seconds() > 10.0
            )
        ):
            evidence.state = observation
            evidence.count = 1
            evidence.first_seen = now
        else:
            evidence.count += 1

        evidence.last_seen = now
        duration = (now - evidence.first_seen).total_seconds()
        stable = (
            evidence.count >= self.minimum_samples
            and duration >= self.minimum_duration_seconds
        )
        return {
            "attention_state": observation if stable else "UNKNOWN",
            "stable": stable,
            "sample_count": evidence.count,
        }

    def clear_session(self, session_id: str) -> None:
        session = str(session_id)
        for key in list(self._evidence):
            if key[0] == session:
                del self._evidence[key]
