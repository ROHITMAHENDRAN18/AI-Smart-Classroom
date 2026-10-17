export function normalizeAttentionStatus(result) {
  return {
    attention_inference: result.attention_inference,
    attention_state: result.attention_state || 'UNKNOWN',
    attention_score: Number.isFinite(result.attention_score)
      ? result.attention_score
      : null,
    attention_confidence: Number.isFinite(result.attention_confidence)
      ? result.attention_confidence
      : 0,
    head_pose: result.head_pose || 'UNKNOWN',
  }
}
