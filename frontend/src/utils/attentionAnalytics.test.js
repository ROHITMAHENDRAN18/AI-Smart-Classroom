import test from 'node:test'
import assert from 'node:assert/strict'

import { summarizeAttentionRecords } from './attentionAnalytics.js'

test('groups each supported state and uses valid observations as denominator', () => {
  const summary = summarizeAttentionRecords([
    { attention_state: 'LISTENING' },
    { attention_state: 'SLEEPING' },
    { attention_state: 'LOOKING_AWAY' },
    { attention_state: 'UNKNOWN' },
  ])

  assert.equal(summary.attention_records, 4)
  assert.equal(summary.valid_attention_records, 4)
  assert.deepEqual(summary.attention_state_counts, {
    LISTENING: 1,
    SLEEPING: 1,
    LOOKING_AWAY: 1,
    UNKNOWN: 1,
  })
  assert.equal(summary.attentive_count, 1)
  assert.equal(summary.not_attentive_count, 2)
  assert.equal(summary.unknown_count, 1)
  assert.equal(summary.attentive_percentage, 25)
  assert.equal(summary.not_attentive_percentage, 50)
  assert.equal(summary.unknown_percentage, 25)
})

test('mixed and legacy observations reconcile without fabricating a category', () => {
  const summary = summarizeAttentionRecords([
    { attention_state: 'LISTENING' },
    { attention_state: 'SLEEPING' },
    { attention_state: 'UNKNOWN' },
    { attention_state: 'ATTENTIVE' },
    { attention_state: 'NOT ATTENTIVE' },
    { attention_state: 'PARTIAL' },
    { attention_state: null },
    { attention_state: 'SOMETHING_NEW' },
  ])

  assert.equal(summary.attention_records, 8)
  assert.equal(summary.valid_attention_records, 3)
  assert.equal(summary.data_quality_records, 5)
  assert.equal(summary.attentive_count + summary.not_attentive_count + summary.unknown_count, 3)
  assert.equal(summary.attentive_percentage, 33.33)
  assert.equal(summary.not_attentive_percentage, 33.33)
  assert.equal(summary.unknown_percentage, 33.33)
  assert.deepEqual(summary.data_quality_state_counts, {
    'LEGACY: ATTENTIVE': 1,
    'LEGACY: NOT ATTENTIVE': 1,
    'LEGACY: PARTIAL': 1,
    NULL: 1,
    SOMETHING_NEW: 1,
  })
})

test('empty selected session returns zero records and zero percentages', () => {
  const summary = summarizeAttentionRecords([])
  assert.equal(summary.attention_records, 0)
  assert.equal(summary.valid_attention_records, 0)
  assert.equal(summary.data_quality_records, 0)
  assert.equal(summary.attentive_percentage, 0)
  assert.equal(summary.not_attentive_percentage, 0)
  assert.equal(summary.unknown_percentage, 0)
})

test('selected-session rows are summarized without incorporating other sessions', () => {
  const rows = [
    { session_id: 'selected', attention_state: 'LISTENING' },
    { session_id: 'selected', attention_state: 'UNKNOWN' },
    { session_id: 'other', attention_state: 'SLEEPING' },
  ]
  const selectedRows = rows.filter((record) => record.session_id === 'selected')
  const summary = summarizeAttentionRecords(selectedRows)
  assert.equal(summary.attention_records, 2)
  assert.equal(summary.attentive_count, 1)
  assert.equal(summary.not_attentive_count, 0)
  assert.equal(summary.unknown_count, 1)
})
