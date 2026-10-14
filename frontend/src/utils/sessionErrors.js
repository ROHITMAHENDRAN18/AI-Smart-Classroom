export function isNoActiveSessionError(error) {
  return (
    error?.response?.status === 404 &&
    error?.response?.data?.detail === 'No active classroom session'
  )
}

export function getSessionErrorMessage(error, action = 'load') {
  if (error?.code === 'ERR_CANCELED') {
    return ''
  }

  if (!error?.response) {
    if (error?.isAxiosError) {
      return 'Cannot reach the classroom session service. Check that the FastAPI backend is running, then retry.'
    }

    return error?.message ||
      'The session service returned an unexpected response. Please retry.'
  }

  const { status } = error.response

  if (status === 401) {
    return 'Your session has expired. Please log in again.'
  }

  if (status === 403) {
    return 'You do not have permission to manage this classroom.'
  }

  if (status === 404) {
    const detail = error.response.data?.detail
    if (detail === 'Not Found') {
      return 'The backend does not have the expected classroom session route. Verify the backend version and API base URL, then restart the backend.'
    }
    if (detail === 'Classroom not found') {
      return 'The configured classroom was not found or is not accessible to your account.'
    }
    return action === 'stop'
      ? 'The selected session or classroom could not be found.'
      : 'The requested classroom session could not be found.'
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
