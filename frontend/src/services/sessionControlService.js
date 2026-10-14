import api from './api'
import { parseClassroomId } from '../utils/classroomConfig'
import { isNoActiveSessionError } from '../utils/sessionErrors'
export { getSessionErrorMessage } from '../utils/sessionErrors'

const classroomConfiguration = parseClassroomId(
  import.meta.env.VITE_DEFAULT_CLASSROOM_ID,
)
export const CLASSROOM_ID = classroomConfiguration.classroomId

export function getConfiguredClassroomId() {
  if (classroomConfiguration.error) {
    throw new Error(classroomConfiguration.error)
  }

  return CLASSROOM_ID
}

function getClassroomId() {
  return getConfiguredClassroomId()
}

function normalizeSession(session) {
  const durationSeconds =
    session?.duration_seconds === null ||
    session?.duration_seconds === undefined
      ? null
      : Number(session.duration_seconds)

  if (
    !session ||
    typeof session !== 'object' ||
    !Number.isSafeInteger(session.id) ||
    typeof session.session_id !== 'string' ||
    !Number.isSafeInteger(session.classroom_id) ||
    typeof session.started_at !== 'string' ||
    typeof session.status !== 'string' ||
    (durationSeconds !== null &&
      (!Number.isSafeInteger(durationSeconds) || durationSeconds < 0))
  ) {
    throw new Error(
      'The session service returned an unexpected response. Please refresh and retry.',
    )
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

function unwrapSession(response) {
  return normalizeSession(response?.session || response)
}

export async function getSessions({
  limit = 50,
  offset = 0,
  signal,
} = {}) {
  const response = await api.get(
    `/classrooms/${getClassroomId()}/sessions`,
    {
      params: { limit, offset },
      signal,
    },
  )

  if (!Array.isArray(response.data)) {
    throw new Error(
      'The session service returned an unexpected history response. Please retry.',
    )
  }

  return response.data.map(normalizeSession)
}

export async function getActiveSession({ signal } = {}) {
  try {
    const response = await api.get(
      `/classrooms/${getClassroomId()}/sessions/active`,
      { signal },
    )

    return normalizeSession(response.data)
  } catch (error) {
    if (isNoActiveSessionError(error)) {
      return null
    }

    throw error
  }
}

export async function startSession({ signal } = {}) {
  const response = await api.post(
    `/classrooms/${getClassroomId()}/sessions`,
    null,
    { signal },
  )

  return unwrapSession(response.data)
}

export async function stopSession(sessionId, { signal } = {}) {
  if (!sessionId || typeof sessionId !== 'string') {
    throw new Error('A valid active session ID is required.')
  }

  const response = await api.post(
    `/classrooms/${getClassroomId()}/sessions/${encodeURIComponent(
      sessionId,
    )}/stop`,
    null,
    { signal },
  )

  return unwrapSession(response.data)
}
