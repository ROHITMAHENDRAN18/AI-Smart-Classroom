import api from './api'

/**
 * Normalize session data structure safely.
 */
export function normalizeSession(session) {
  if (!session) {
    return null
  }

  return {
    id: session.id ?? null,
    session_id: session.session_id ?? session.sessionId ?? '',
    started_at: session.started_at ?? session.startedAt ?? null,
    ended_at: session.ended_at ?? session.endedAt ?? null,
    duration_seconds:
      session.duration_seconds !== null && session.duration_seconds !== undefined
        ? Number(session.duration_seconds)
        : null,
    status: String(session.status || 'UNKNOWN').toUpperCase(),
    created_at: session.created_at ?? session.createdAt ?? null,
  }
}

/**
 * Normalize session summary and statistical metrics safely.
 */
export function normalizeSessionSummary(data) {
  if (!data) {
    return null
  }

  const rawStats = data.statistics || {}
  const rawSession = data.session || {}

  const uniqueStudents = Number(rawStats.unique_students ?? 0)
  const attendanceRecords = Number(rawStats.attendance_records ?? 0)
  const attentionRecords = Number(rawStats.attention_records ?? 0)
  const attentiveCount = Number(rawStats.attentive_count ?? 0)
  const notAttentiveCount = Number(rawStats.not_attentive_count ?? 0)
  const unknownCount = Number(rawStats.unknown_count ?? 0)

  const attentivePct = Number(rawStats.attentive_percentage ?? 0)
  const notAttentivePct = Number(rawStats.not_attentive_percentage ?? 0)
  const unknownPct = Number(rawStats.unknown_percentage ?? 0)

  return {
    session: normalizeSession(rawSession),
    attendance: Array.isArray(data.attendance) ? data.attendance : [],
    attention: Array.isArray(data.attention) ? data.attention : [],
    statistics: {
      unique_students: Number.isFinite(uniqueStudents) ? uniqueStudents : 0,
      student_ids: Array.isArray(rawStats.student_ids) ? rawStats.student_ids : [],
      attendance_records: Number.isFinite(attendanceRecords) ? attendanceRecords : 0,
      attention_records: Number.isFinite(attentionRecords) ? attentionRecords : 0,
      attentive_count: Number.isFinite(attentiveCount) ? attentiveCount : 0,
      not_attentive_count: Number.isFinite(notAttentiveCount) ? notAttentiveCount : 0,
      unknown_count: Number.isFinite(unknownCount) ? unknownCount : 0,
      attentive_percentage: Number.isFinite(attentivePct) ? attentivePct : 0.0,
      not_attentive_percentage: Number.isFinite(notAttentivePct) ? notAttentivePct : 0.0,
      unknown_percentage: Number.isFinite(unknownPct) ? unknownPct : 0.0,
    },
  }
}

/**
 * Fetch all past and current sessions from history API.
 */
export async function getHistorySessions(limit = 50, offset = 0) {
  const response = await api.get('/history/sessions', {
    params: {
      limit,
      offset,
    },
  })

  const sessions = Array.isArray(response.data) ? response.data : []
  return sessions.map(normalizeSession)
}

/**
 * Fetch details for a specific session by session_id.
 */
export async function getHistorySession(sessionId) {
  if (!sessionId) {
    throw new Error('A session ID is required.')
  }

  const response = await api.get(
    `/history/sessions/${encodeURIComponent(sessionId)}`,
  )

  return normalizeSession(response.data)
}

/**
 * Fetch summary and statistics for a specific session by session_id.
 */
export async function getSessionSummary(sessionId) {
  if (!sessionId) {
    throw new Error('A session ID is required.')
  }

  const response = await api.get(
    `/history/sessions/${encodeURIComponent(sessionId)}/summary`,
  )

  return normalizeSessionSummary(response.data)
}

/**
 * Fetch attendance records for a specific session by session_id.
 */
export async function getSessionAttendance(sessionId) {
  if (!sessionId) {
    throw new Error('A session ID is required.')
  }

  const response = await api.get(
    `/history/sessions/${encodeURIComponent(sessionId)}/attendance`,
  )

  return Array.isArray(response.data) ? response.data : []
}

/**
 * Fetch attention records for a specific session by session_id.
 */
export async function getSessionAttention(sessionId) {
  if (!sessionId) {
    throw new Error('A session ID is required.')
  }

  const response = await api.get(
    `/history/sessions/${encodeURIComponent(sessionId)}/attention`,
  )

  return Array.isArray(response.data) ? response.data : []
}
