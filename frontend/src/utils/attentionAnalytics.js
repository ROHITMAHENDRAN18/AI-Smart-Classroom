const SUPPORTED_STATES = new Set([
  'LISTENING',
  'SLEEPING',
  'LOOKING_AWAY',
  'UNKNOWN',
])

const LEGACY_STATES = new Set([
  'ATTENTIVE',
  'NOT ATTENTIVE',
  'PARTIAL',
])

export function summarizeAttentionRecords(records = []) {
  const stateCounts = {
    LISTENING: 0,
    SLEEPING: 0,
    LOOKING_AWAY: 0,
    UNKNOWN: 0,
  }
  const dataQualityStateCounts = {}

  for (const record of records) {
    let state = record?.attention_state
    if (state === null || state === undefined) {
      state = 'NULL'
    } else {
      state = String(state).trim().toUpperCase()
      if (!state) state = 'EMPTY'
      if (state === 'LOOKING AWAY') state = 'LOOKING_AWAY'
      if (state === 'NOT_ATTENTIVE' || state === 'NOTATTENTIVE') {
        state = 'NOT ATTENTIVE'
      }
    }

    if (SUPPORTED_STATES.has(state)) {
      stateCounts[state] += 1
      continue
    }

    const qualityLabel = LEGACY_STATES.has(state)
      ? `LEGACY: ${state}`
      : state
    dataQualityStateCounts[qualityLabel] =
      (dataQualityStateCounts[qualityLabel] || 0) + 1
  }

  const attentionRecords = records.length
  const validAttentionRecords = Object.values(stateCounts).reduce(
    (total, count) => total + count,
    0,
  )
  const attentiveCount = stateCounts.LISTENING
  const notAttentiveCount = stateCounts.SLEEPING + stateCounts.LOOKING_AWAY
  const unknownCount = stateCounts.UNKNOWN
  const percentage = (count) => validAttentionRecords
    ? Number(((count / validAttentionRecords) * 100).toFixed(2))
    : 0

  return {
    attention_records: attentionRecords,
    valid_attention_records: validAttentionRecords,
    data_quality_records: attentionRecords - validAttentionRecords,
    data_quality_state_counts: dataQualityStateCounts,
    attention_state_counts: stateCounts,
    attentive_count: attentiveCount,
    not_attentive_count: notAttentiveCount,
    unknown_count: unknownCount,
    partial_count: 0,
    attentive_percentage: percentage(attentiveCount),
    not_attentive_percentage: percentage(notAttentiveCount),
    unknown_percentage: percentage(unknownCount),
    partial_percentage: 0,
  }
}
