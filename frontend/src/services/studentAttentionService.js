import axios from 'axios'

const monitoringApi = axios.create({
  baseURL: '/monitoring',
  timeout: 5000,
})

export async function getStudentAttention() {
  const response = await monitoringApi.get('/api/state')

  return response.data
}

export function normalizeStudentAttention(data) {
  const students =
    Array.isArray(data?.students)
      ? data.students
      : Array.isArray(data?.dashboard_students)
        ? data.dashboard_students
        : []

  return students.map((student, index) => {
    const similarity = Number(student?.similarity)

    return {
      trackId:
        student?.track_id ??
        student?.trackId ??
        index + 1,

      studentId:
        student?.student_id ??
        student?.studentId ??
        null,

      recognized:
        Boolean(student?.recognized),

      similarity:
        Number.isFinite(similarity)
          ? similarity
          : 0,

      attention:
        normalizeAttentionState(
          student?.attention,
        ),

      yawRatio:
        toNullableNumber(
          student?.yaw_ratio ??
            student?.yawRatio,
        ),

      pitchRatio:
        toNullableNumber(
          student?.pitch_ratio ??
            student?.pitchRatio,
        ),
    }
  })
}

function normalizeAttentionState(value) {
  const normalized = String(
    value ?? 'UNKNOWN',
  )
    .trim()
    .toUpperCase()

  if (normalized === 'ATTENTIVE') {
    return 'ATTENTIVE'
  }

  if (
    normalized === 'NOT ATTENTIVE' ||
    normalized === 'NOT_ATTENTIVE' ||
    normalized === 'NOTATTENTIVE'
  ) {
    return 'NOT ATTENTIVE'
  }

  return 'UNKNOWN'
}

function toNullableNumber(value) {
  const number = Number(value)

  return Number.isFinite(number)
    ? number
    : null
}