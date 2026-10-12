import api from './api'

/**
 * Normalizes a student entity safely.
 */
export function normalizeStudent(student) {
  if (!student) {
    return null
  }

  return {
    id: student.id ?? null,
    student_id: student.student_id ?? student.studentId ?? '',
    name: student.name ?? 'Unknown Student',
    department: student.department ?? '—',
    year: student.year ?? '—',
    section: student.section ?? '—',
    email: student.email ?? null,
    face_registered: Boolean(student.face_registered ?? student.faceRegistered),
    is_active: Boolean(student.is_active ?? student.isActive ?? true),
  }
}

/**
 * Normalizes a classroom session record safely.
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
 * Normalizes an attendance history entry.
 */
export function normalizeAttendanceRecord(record) {
  if (!record) {
    return null
  }

  return {
    id: record.id ?? null,
    session_id: record.session_id ?? record.sessionId ?? '',
    student_id: record.student_id ?? record.studentId ?? '',
    status: String(record.status || 'UNKNOWN').toUpperCase(),
    confidence:
      record.confidence !== null && record.confidence !== undefined
        ? Number(record.confidence)
        : null,
    recorded_at: record.recorded_at ?? record.recordedAt ?? null,
  }
}

/**
 * Normalizes an attention history entry.
 */
export function normalizeAttentionRecord(record) {
  if (!record) {
    return null
  }

  return {
    id: record.id ?? null,
    session_id: record.session_id ?? record.sessionId ?? '',
    student_id: record.student_id ?? record.studentId ?? '',
    track_id: record.track_id ?? record.trackId ?? null,
    attention_state: String(
      record.attention_state ?? record.attentionState ?? 'UNKNOWN',
    ).toUpperCase(),
    confidence:
      record.confidence !== null && record.confidence !== undefined
        ? Number(record.confidence)
        : null,
    recorded_at: record.recorded_at ?? record.recordedAt ?? null,
  }
}

/**
 * Fetch all registered students from /students.
 */
export async function getStudents() {
  const response = await api.get('/students')
  const students = Array.isArray(response.data) ? response.data : []
  return students.map(normalizeStudent)
}

/**
 * Fetch specific student details by student_id.
 */
export async function getStudent(studentId) {
  if (!studentId) {
    throw new Error('Student ID is required.')
  }

  const response = await api.get(`/students/${encodeURIComponent(studentId)}`)
  return normalizeStudent(response.data)
}

/**
 * Fetch session history list from /history/sessions.
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
 * Fetch session summary from /history/sessions/{session_id}/summary.
 */
export async function getSessionSummary(sessionId) {
  if (!sessionId) {
    throw new Error('Session ID is required.')
  }

  const response = await api.get(
    `/history/sessions/${encodeURIComponent(sessionId)}/summary`,
  )

  return response.data
}

/**
 * Fetch attendance records for a specific session.
 */
export async function getSessionAttendance(sessionId) {
  if (!sessionId) {
    throw new Error('Session ID is required.')
  }

  const response = await api.get(
    `/history/sessions/${encodeURIComponent(sessionId)}/attendance`,
  )

  const records = Array.isArray(response.data) ? response.data : []
  return records.map(normalizeAttendanceRecord)
}

/**
 * Fetch attention records for a specific session.
 */
export async function getSessionAttention(sessionId) {
  if (!sessionId) {
    throw new Error('Session ID is required.')
  }

  const response = await api.get(
    `/history/sessions/${encodeURIComponent(sessionId)}/attention`,
  )

  const records = Array.isArray(response.data) ? response.data : []
  return records.map(normalizeAttentionRecord)
}

/**
 * Fetch student-level analytics from /analytics/students/{student_id}.
 */
export async function getStudentAnalytics(studentId) {
  if (!studentId) {
    return null
  }

  try {
    const response = await api.get(
      `/analytics/students/${encodeURIComponent(studentId)}`,
    )
    return response.data
  } catch (error) {
    // If student has no analytics yet, return null
    if (error.response?.status === 404) {
      return null
    }
    throw error
  }
}

/**
 * Resolve existing student HTML report URL (via /monitoring proxy).
 */
export function getStudentReportUrl(studentId) {
  if (!studentId) {
    return null
  }

  return `/monitoring/reports/student/${encodeURIComponent(studentId)}`
}
