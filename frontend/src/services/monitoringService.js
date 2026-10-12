import api from './api'

export class MonitoringServiceError extends Error {
  constructor(message) {
    super(message)
    this.name = 'MonitoringServiceError'
  }
}

function normalizeAlert(alert) {
  if (
    !alert ||
    typeof alert !== 'object' ||
    typeof alert.alert_id !== 'string' ||
    typeof alert.alert_type !== 'string' ||
    typeof alert.message !== 'string' ||
    typeof alert.timestamp !== 'string' ||
    typeof alert.session_id !== 'string' ||
    typeof alert.student_id !== 'string' ||
    (alert.severity !== null && typeof alert.severity !== 'string') ||
    (alert.track_id !== null && typeof alert.track_id !== 'number')
  ) {
    throw new MonitoringServiceError(
      'The alert service returned an unexpected response. Please retry.',
    )
  }

  return {
    alert_id: alert.alert_id,
    alert_type: alert.alert_type,
    message: alert.message,
    severity: alert.severity,
    timestamp: alert.timestamp,
    session_id: alert.session_id,
    student_id: alert.student_id,
    track_id: alert.track_id,
  }
}

export async function getMonitoringAlerts({
  limit = 50,
  offset = 0,
  sessionId,
  signal,
} = {}) {
  const params = { limit, offset }

  if (sessionId) {
    params.session_id = sessionId
  }

  const response = await api.get('/alerts', {
    params,
    signal,
  })

  if (!Array.isArray(response.data)) {
    throw new MonitoringServiceError(
      'The alert service returned an unexpected response. Please retry.',
    )
  }

  return response.data.map(normalizeAlert)
}

export function getMonitoringErrorMessage(error) {
  if (error instanceof MonitoringServiceError) {
    return error.message
  }

  if (error?.code === 'ERR_CANCELED') {
    return ''
  }

  if (error?.isAxiosError) {
    if (error.code === 'ECONNABORTED' || !error.response) {
      return 'Cannot reach the alert service. Check that the FastAPI backend is running, then retry.'
    }

    const { status } = error.response

    if (status === 401) {
      return 'Your session has expired. Please log in again.'
    }

    if (status === 403) {
      return 'You do not have permission to view these alerts.'
    }

    if (status >= 500) {
      return 'The alert service encountered a server error. Please retry shortly.'
    }

    return `The alert request failed (HTTP ${status}). Please retry.`
  }

  return 'Unable to load alerts. Please retry.'
}
