import api from './api'
import { CLASSROOM_ID } from './sessionControlService'

function requireClassroomId(classroomId) {
  if (!Number.isSafeInteger(classroomId) || classroomId < 1) {
    throw new Error(
      'Set VITE_DEFAULT_CLASSROOM_ID to a valid classroom ID before loading classroom data.',
    )
  }
  return classroomId
}

function requireArray(data, label) {
  if (!Array.isArray(data)) {
    throw new Error(`The ${label} service returned an unexpected response.`)
  }
  return data
}

export function normalizeStudent(student) {
  if (
    !student ||
    !Number.isSafeInteger(student.id) ||
    typeof student.student_id !== 'string' ||
    typeof student.name !== 'string' ||
    typeof student.department !== 'string' ||
    !Number.isSafeInteger(student.year) ||
    typeof student.section !== 'string' ||
    typeof student.face_registered !== 'boolean' ||
    (student.classroom_is_active !== undefined &&
      student.classroom_is_active !== null &&
      typeof student.classroom_is_active !== 'boolean')
  ) {
    throw new Error('The student service returned an unexpected student record.')
  }

  return {
    id: student.id,
    student_id: student.student_id,
    name: student.name,
    department: student.department,
    year: student.year,
    section: student.section,
    email: student.email ?? null,
    face_registered: student.face_registered,
    classroom_is_active: student.classroom_is_active ?? null,
  }
}

export function normalizeSession(session) {
  if (
    !session ||
    !Number.isSafeInteger(session.id) ||
    typeof session.session_id !== 'string' ||
    !Number.isSafeInteger(session.classroom_id) ||
    typeof session.started_at !== 'string' ||
    typeof session.status !== 'string'
  ) {
    throw new Error('The session service returned an unexpected session record.')
  }

  const durationSeconds =
    session.duration_seconds === null ||
    session.duration_seconds === undefined
      ? null
      : Number(session.duration_seconds)
  if (
    durationSeconds !== null &&
    (!Number.isSafeInteger(durationSeconds) || durationSeconds < 0)
  ) {
    throw new Error('The session service returned an invalid duration.')
  }

  return {
    id: session.id,
    session_id: session.session_id,
    classroom_id: session.classroom_id,
    started_at: session.started_at,
    ended_at: session.ended_at ?? null,
    duration_seconds: durationSeconds,
    status: session.status.toUpperCase(),
    created_at: session.created_at ?? null,
  }
}

export function normalizeAttendanceRecord(record) {
  if (
    !record ||
    !Number.isSafeInteger(record.id) ||
    typeof record.session_id !== 'string' ||
    typeof record.student_id !== 'string' ||
    typeof record.status !== 'string' ||
    typeof record.recorded_at !== 'string'
  ) {
    throw new Error(
      'The attendance service returned an unexpected attendance record.',
    )
  }
  const confidence =
    record.confidence === null || record.confidence === undefined
      ? null
      : Number(record.confidence)
  if (confidence !== null && !Number.isFinite(confidence)) {
    throw new Error('The attendance service returned invalid confidence data.')
  }
  return {
    id: record.id,
    session_id: record.session_id,
    student_id: record.student_id,
    student_name: record.student_name ?? null,
    status: record.status.trim().toUpperCase(),
    confidence,
    recorded_at: record.recorded_at,
  }
}

export function normalizeAttendanceStatus(value) {
  const status = String(value ?? 'UNKNOWN')
    .trim()
    .toUpperCase()
    .replace(/-/g, '_')
    .replace(/\s+/g, '_')
  if (status === 'PRESENT' || status === 'P') return 'PRESENT'
  if (status === 'ABSENT' || status === 'A') return 'ABSENT'
  return 'UNKNOWN'
}

export function normalizeAttendanceReport(data) {
  const countFields = [
    'total_records',
    'present_count',
    'absent_count',
    'unknown_count',
    'limit',
    'offset',
  ]
  if (
    !data ||
    typeof data !== 'object' ||
    !Number.isSafeInteger(data.classroom_id) ||
    typeof data.from_date !== 'string' ||
    typeof data.to_date !== 'string' ||
    typeof data.generated_at !== 'string' ||
    !countFields.every(
      (field) => Number.isSafeInteger(data[field]) && data[field] >= 0,
    ) ||
    !Array.isArray(data.records) ||
    !Array.isArray(data.daily_trend) ||
    (data.attendance_rate !== null &&
      !Number.isFinite(data.attendance_rate))
  ) {
    throw new Error(
      'The classroom attendance service returned an unexpected response.',
    )
  }
  return {
    ...data,
    records: data.records.map(normalizeAttendanceRecord),
  }
}

export async function getStudents({
  classroomId = CLASSROOM_ID,
  signal,
} = {}) {
  const response = await api.get('/students', {
    params: { classroom_id: requireClassroomId(classroomId) },
    signal,
  })
  return requireArray(response.data, 'student').map(normalizeStudent)
}

export async function getClassroomSessions({
  classroomId = CLASSROOM_ID,
  limit = 50,
  offset = 0,
  signal,
} = {}) {
  const response = await api.get(
    `/classrooms/${requireClassroomId(classroomId)}/sessions`,
    {
      params: { limit, offset },
      signal,
    },
  )
  return requireArray(response.data, 'classroom session').map(normalizeSession)
}

export async function getHistorySessions(
  limit = 50,
  offset = 0,
  { classroomId = CLASSROOM_ID, signal } = {},
) {
  return getClassroomSessions({ classroomId, limit, offset, signal })
}

export async function getClassroomAttendance({
  classroomId = CLASSROOM_ID,
  date,
  fromDate,
  toDate,
  sessionId,
  limit = 50,
  offset = 0,
  signal,
} = {}) {
  const response = await api.get(
    `/classrooms/${requireClassroomId(classroomId)}/attendance`,
    {
      params: {
        date,
        from_date: fromDate,
        to_date: toDate,
        session_id: sessionId || undefined,
        limit,
        offset,
      },
      signal,
    },
  )
  return normalizeAttendanceReport(response.data)
}

export async function getSessionSummary(sessionId, { signal } = {}) {
  if (!sessionId || typeof sessionId !== 'string') {
    throw new Error('A session ID is required.')
  }
  const response = await api.get(
    `/history/sessions/${encodeURIComponent(sessionId)}/summary`,
    { signal },
  )
  const data = response.data
  if (
    !data ||
    typeof data !== 'object' ||
    !data.session ||
    !Array.isArray(data.attendance) ||
    !Array.isArray(data.attention) ||
    !data.statistics ||
    !Number.isSafeInteger(data.statistics.unique_students) ||
    !Number.isSafeInteger(data.statistics.attendance_records) ||
    !Number.isSafeInteger(data.statistics.attention_records)
  ) {
    throw new Error('The analytics service returned an unexpected response.')
  }
  return data
}

export async function getSessionAttendance(
  sessionId,
  { signal, fromDate, toDate } = {},
) {
  if (!sessionId || typeof sessionId !== 'string') {
    throw new Error('A session ID is required.')
  }
  const response = await api.get(
    `/history/sessions/${encodeURIComponent(sessionId)}/attendance`,
    {
      params: { from_date: fromDate, to_date: toDate },
      signal,
    },
  )
  return requireArray(response.data, 'attendance').map(normalizeAttendanceRecord)
}

export async function getSessionAttention(
  sessionId,
  { signal, fromDate, toDate } = {},
) {
  if (!sessionId || typeof sessionId !== 'string') {
    throw new Error('A session ID is required.')
  }
  const response = await api.get(
    `/history/sessions/${encodeURIComponent(sessionId)}/attention`,
    {
      params: { from_date: fromDate, to_date: toDate },
      signal,
    },
  )
  return requireArray(response.data, 'attention')
}

export async function getStudentAnalytics(
  studentId,
  { classroomId = CLASSROOM_ID, signal } = {},
) {
  if (!studentId || typeof studentId !== 'string') {
    throw new Error('A student ID is required.')
  }
  const response = await api.get(
    `/analytics/students/${encodeURIComponent(studentId)}`,
    {
      params: { classroom_id: requireClassroomId(classroomId) },
      signal,
    },
  )
  return response.data
}
