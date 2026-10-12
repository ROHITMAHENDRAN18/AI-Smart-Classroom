import api from './api'

export class FrameInferenceServiceError extends Error {
  constructor(message) {
    super(message)
    this.name = 'FrameInferenceServiceError'
  }
}

export class MonitoringServiceError extends Error {
  constructor(message) {
    super(message)
    this.name = 'MonitoringServiceError'
  }
}

function normalizeFrameInference(result) {
  const featureNames = [
    'person_detection',
    'face_detection',
    'face_recognition',
    'tracking',
    'attention_estimation',
    'attendance',
  ]
  const validDetection = (detection) =>
    detection &&
    detection.class_label === 'person' &&
    Number.isFinite(detection.x1) &&
    Number.isFinite(detection.y1) &&
    Number.isFinite(detection.x2) &&
    Number.isFinite(detection.y2) &&
    Number.isFinite(detection.confidence) &&
    detection.x1 >= 0 &&
    detection.y1 >= 0 &&
    detection.x2 > detection.x1 &&
    detection.y2 > detection.y1 &&
    detection.confidence >= 0 &&
    detection.confidence <= 1

  if (
    !result ||
    typeof result !== 'object' ||
    typeof result.session_id !== 'string' ||
    !Number.isSafeInteger(result.classroom_id) ||
    !Number.isSafeInteger(result.frame_width) ||
    result.frame_width < 1 ||
    !Number.isSafeInteger(result.frame_height) ||
    result.frame_height < 1 ||
    typeof result.frame_received_at !== 'string' ||
    typeof result.processed_at !== 'string' ||
    result.processing_status !== 'completed' ||
    !Number.isFinite(result.inference_duration_ms) ||
    result.inference_duration_ms < 0 ||
    result.pipeline !== 'person_detection' ||
    result.attention_inference !== 'not_connected' ||
    !result.features ||
    !featureNames.every(
      (name) =>
        result.features[name] &&
        ['available', 'not_connected'].includes(
          result.features[name].status,
        ) &&
        typeof result.features[name].detail === 'string',
    ) ||
    result.features.person_detection.status !== 'available' ||
    !Array.isArray(result.detections) ||
    !result.detections.every(
      (detection) =>
        validDetection(detection) &&
        detection.x2 <= result.frame_width &&
        detection.y2 <= result.frame_height,
    ) ||
    result.detection_count !== result.detections.length ||
    typeof result.results_persisted !== 'boolean'
  ) {
    throw new FrameInferenceServiceError(
      'The inference service returned an unexpected response. Retry the frame.',
    )
  }

  return {
    session_id: result.session_id,
    classroom_id: result.classroom_id,
    frame_received_at: result.frame_received_at,
    processed_at: result.processed_at,
    frame_width: result.frame_width,
    frame_height: result.frame_height,
    processing_status: result.processing_status,
    inference_duration_ms: result.inference_duration_ms,
    pipeline: result.pipeline,
    attention_inference: result.attention_inference,
    features: Object.fromEntries(
      featureNames.map((name) => [
        name,
        {
          status: result.features[name].status,
          detail: result.features[name].detail,
        },
      ]),
    ),
    detections: result.detections.map((detection) => ({
      class_label: detection.class_label,
      x1: detection.x1,
      y1: detection.y1,
      x2: detection.x2,
      y2: detection.y2,
      confidence: detection.confidence,
    })),
    detection_count: result.detection_count,
    results_persisted: result.results_persisted,
  }
}

export async function analyzeMonitoringFrame({
  classroomId,
  sessionId,
  frame,
  signal,
}) {
  if (!Number.isSafeInteger(classroomId) || classroomId < 1) {
    throw new FrameInferenceServiceError(
      'Configure a valid classroom before sending camera frames.',
    )
  }
  if (
    !sessionId ||
    typeof sessionId !== 'string' ||
    typeof Blob === 'undefined' ||
    !(frame instanceof Blob)
  ) {
    throw new FrameInferenceServiceError(
      'A valid active session and camera frame are required.',
    )
  }

  const response = await api.post(
    `/classrooms/${classroomId}/sessions/${encodeURIComponent(sessionId)}/frames`,
    frame,
    {
      headers: { 'Content-Type': 'image/jpeg' },
      signal,
      timeout: 30000,
    },
  )

  return normalizeFrameInference(response.data)
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

export function getFrameInferenceErrorMessage(error) {
  if (error instanceof FrameInferenceServiceError) {
    return error.message
  }

  if (error?.code === 'ERR_CANCELED') {
    return ''
  }

  if (error?.isAxiosError) {
    if (error.code === 'ECONNABORTED' || !error.response) {
      return 'Cannot reach frame inference. Check that the backend and configured person-detection model are available, then retry.'
    }

    const { status } = error.response
    if (status === 401) {
      return 'Your session has expired. Please log in again.'
    }
    if (status === 403) {
      return 'You do not have permission to process frames for this classroom.'
    }
    if (status === 404) {
      return 'The active classroom session could not be found. Refresh session status before retrying.'
    }
    if (status === 413) {
      return 'The captured frame is too large. Reduce camera resolution and retry.'
    }
    if (status === 415 || status === 422) {
      return 'The backend rejected the captured frame. Check camera output and retry.'
    }
    if (status === 429) {
      return 'Frames are arriving too quickly. The application will retry at a slower rate.'
    }
    if (status === 503) {
      return 'Person detection is busy or unavailable. Check the backend model setup and retry.'
    }
    if (status === 504) {
      return 'Person detection took too long. The application will retry with the next sampled frame.'
    }
    if (status >= 500) {
      return 'Frame inference encountered a server error. Please retry shortly.'
    }
    return `Frame inference failed (HTTP ${status}). Please retry.`
  }

  return 'Unable to process the camera frame. Please retry.'
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
