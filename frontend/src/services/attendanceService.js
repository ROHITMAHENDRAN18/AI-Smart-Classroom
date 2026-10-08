import axios from 'axios'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  'http://127.0.0.1:8000/api/v1'

const attendanceApi = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
})

export async function getAttendanceSessions(
  limit = 50,
  offset = 0,
) {
  const response = await attendanceApi.get(
    '/history/sessions',
    {
      params: {
        limit,
        offset,
      },
    },
  )

  return Array.isArray(response.data)
    ? response.data
    : []
}

export async function getSessionAttendance(
  sessionId,
) {
  if (!sessionId) {
    throw new Error(
      'A session ID is required.',
    )
  }

  const response = await attendanceApi.get(
    `/history/sessions/${encodeURIComponent(
      sessionId,
    )}/attendance`,
  )

  return Array.isArray(response.data)
    ? response.data
    : []
}

export async function getSessionSummary(
  sessionId,
) {
  if (!sessionId) {
    throw new Error(
      'A session ID is required.',
    )
  }

  const response = await attendanceApi.get(
    `/history/sessions/${encodeURIComponent(
      sessionId,
    )}/summary`,
  )

  return response.data
}

export function normalizeAttendanceRecords(
  records,
) {
  if (!Array.isArray(records)) {
    return []
  }

  return records.map((record) => ({
    id: record?.id ?? null,

    sessionId:
      record?.session_id ??
      record?.sessionId ??
      '',

    studentId:
      record?.student_id ??
      record?.studentId ??
      'UNKNOWN',

    status:
      normalizeAttendanceStatus(
        record?.status,
      ),

    confidence:
      toNullableNumber(
        record?.confidence,
      ),

    recordedAt:
      record?.recorded_at ??
      record?.recordedAt ??
      null,
  }))
}

export function normalizeAttendanceStatus(
  value,
) {
  const normalized = String(
    value ?? 'UNKNOWN',
  )
    .trim()
    .toUpperCase()
    .replace(/-/g, '_')
    .replace(/\s+/g, '_')

  if (
    normalized === 'PRESENT' ||
    normalized === 'P'
  ) {
    return 'PRESENT'
  }

  if (
    normalized === 'ABSENT' ||
    normalized === 'A'
  ) {
    return 'ABSENT'
  }

  return 'UNKNOWN'
}

function toNullableNumber(value) {
  if (
    value === null ||
    value === undefined ||
    value === ''
  ) {
    return null
  }

  const number = Number(value)

  return Number.isFinite(number)
    ? number
    : null
}