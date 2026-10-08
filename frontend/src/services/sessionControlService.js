import api from './api'

const CLASSROOM_ID = 2

function normalizeSession(session) {
  if (!session) {
    return null
  }

  return {
    id: session.id,
    session_id: session.session_id,
    classroom_id: session.classroom_id,
    started_at: session.started_at,
    ended_at: session.ended_at ?? null,
    duration_seconds: session.duration_seconds ?? null,
    status: String(session.status || '').toUpperCase(),
    created_at: session.created_at,
  }
}

export async function getSessions() {
  const response = await api.get(
    `/classrooms/${CLASSROOM_ID}/sessions`,
  )

  const sessions = Array.isArray(response.data)
    ? response.data
    : []

  return sessions.map(normalizeSession)
}

export async function getActiveSession() {
  try {
    const response = await api.get(
      `/classrooms/${CLASSROOM_ID}/sessions/active`,
    )

    return normalizeSession(response.data)
  } catch (error) {
    /*
     * 404 means there is currently no active session.
     * This is a valid application state, not a backend failure.
     */
    if (error.response?.status === 404) {
      return null
    }

    throw error
  }
}

export async function startSession() {
  const response = await api.post(
    `/classrooms/${CLASSROOM_ID}/sessions`,
  )

  return normalizeSession(
    response.data?.session || response.data,
  )
}

export async function stopSession(sessionId) {
  if (!sessionId) {
    throw new Error('Active session ID is missing.')
  }

  const response = await api.post(
    `/classrooms/${CLASSROOM_ID}/sessions/${encodeURIComponent(
      sessionId,
    )}/stop`,
  )

  return normalizeSession(
    response.data?.session || response.data,
  )
}

export { CLASSROOM_ID }