import assert from 'node:assert/strict'
import test from 'node:test'

import { normalizeAttentionStatus } from './monitoringStatus.js'

function response() {
  const features = [
    'person_detection',
    'result_persistence',
    'face_detection',
    'face_recognition',
    'tracking',
    'attention_estimation',
    'head_pose_estimation',
    'eye_state_estimation',
    'attention_persistence',
    'attendance',
  ]
  return {
    session_id: 'SESSION_TEST',
    classroom_id: 1,
    frame_received_at: '2026-10-18T00:00:00Z',
    processed_at: '2026-10-18T00:00:00Z',
    frame_width: 100,
    frame_height: 80,
    processing_status: 'completed',
    inference_duration_ms: 12,
    pipeline: 'person_detection',
    attention_inference: 'partial',
    attention_state: 'UNKNOWN',
    attention_score: null,
    attention_confidence: 0,
    head_pose: 'UNKNOWN',
    features: Object.fromEntries(features.map((name) => [name, {
      status: name === 'person_detection' ? 'available' : 'not_connected',
      detail: `${name} status`,
    }])),
    detections: [],
    face_detections: [{
      recognition_status: 'unknown',
      head_pose: { head_pose: 'UNKNOWN' },
      eye_state: 'UNKNOWN',
      attention_state: 'UNKNOWN',
      attention_score: null,
      attention_confidence: 0,
    }],
    detection_count: 0,
    results_persisted: true,
  }
}

test('normalizes partial capability and UNKNOWN attention without inventing a score', () => {
  const source = response()
  const normalized = normalizeAttentionStatus(source)
  assert.equal(normalized.attention_inference, 'partial')
  assert.equal(normalized.attention_state, 'UNKNOWN')
  assert.equal(normalized.attention_score, null)
  assert.equal(source.features.eye_state_estimation.status, 'not_connected')
  assert.equal(source.face_detections[0].attention_state, 'UNKNOWN')
})
