import api from './api'

const configuredClassroomId = import.meta.env.VITE_DEFAULT_CLASSROOM_ID
export const CLASSROOM_ID = configuredClassroomId
  ? Number(configuredClassroomId)
  : null

function getClassroomId() {
  if (!Number.isSafeInteger(CLASSROOM_ID) || CLASSROOM_ID < 1) {
    throw new Error(
      'Set VITE_DEFAULT_CLASSROOM_ID to a valid classroom ID before using Session Control.',
    )
  }

  return CLASSROOM_ID
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
    if (
      error.response?.status === 404 &&
      error.response?.data?.detail === 'No active classroom session'
    ) {
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

export function getSessionErrorMessage(error, action = 'load') {
  if (error?.code === 'ERR_CANCELED') {
    return ''
  }

  if (!error?.response) {
    return error?.message?.startsWith('Set VITE_DEFAULT_CLASSROOM_ID')
      ? error.message
      : 'Cannot reach the classroom session service. Check that the FastAPI backend is running, then retry.'
  }

  const { status } = error.response

  if (status === 401) {
    return 'Your session has expired. Please log in again.'
  }

  if (status === 403) {
    return 'You do not have permission to manage this classroom.'
  }

  if (status === 404) {
    return action === 'stop'
      ? 'The selected session or classroom could not be found.'
      : 'The configured classroom could not be found.'
  }

  if (status === 409) {
    return action === 'start'
      ? 'An active classroom session already exists. Refresh to load it.'
      : 'This session is no longer active. Refresh the session status.'
  }

  if (status === 400 || status === 422) {
    return 'The session request was invalid. Check the classroom configuration and retry.'
  }

  if (status >= 500) {
    return 'The session service encountered a server error. Please retry shortly.'
  }

  return `The session request failed (HTTP ${status}). Please retry.`
}
