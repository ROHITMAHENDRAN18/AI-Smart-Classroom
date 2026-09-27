"""Temporal smoothing utilities for classroom attention signals."""

from .temporal_smoother import (
    AttentionTemporalSmoother,
    SmoothedAttentionResult,
)

__all__ = ["AttentionTemporalSmoother", "SmoothedAttentionResult"]
