import { useCallback, useEffect, useRef, useState } from 'react'
import {
  Activity,
  AlertCircle,
  Camera,
  CameraOff,
  CheckCircle2,
  CircleHelp,
  LoaderCircle,
  Play,
  RefreshCw,
  ShieldCheck,
  Square,
  Wifi,
  WifiOff,
} from 'lucide-react'

import {
  CLASSROOM_ID,
  getActiveSession,
  getSessionErrorMessage,
  startSession,
  stopSession,
} from '../services/sessionControlService'
import {
  analyzeMonitoringFrame,
  getMonitoringSummary,
  getFrameInferenceErrorMessage,
} from '../services/monitoringService'
import {
  EMPTY_DETECTION_OVERLAY,
  expirePersonDetectionOverlay,
  getNextPersonDetectionExpiry,
  toVideoCoordinates,
  updatePersonDetectionOverlay,
} from '../utils/personDetectionOverlay'
import { notifyClassroomDataChanged } from '../utils/classroomDataEvents'

function boundedNumber(value, fallback, minimum, maximum) {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed === 0) {
    return fallback
  }
  return Math.min(maximum, Math.max(minimum, parsed))
}

const FRAME_CAPTURE_INTERVAL_MS = boundedNumber(
  import.meta.env.VITE_FRAME_CAPTURE_INTERVAL_MS,
  2500,
  2000,
  10000,
)
const FRAME_CAPTURE_MAX_EDGE = boundedNumber(
  import.meta.env.VITE_FRAME_CAPTURE_MAX_EDGE,
  960,
  320,
  1280,
)
const FRAME_JPEG_QUALITY = boundedNumber(
  import.meta.env.VITE_FRAME_JPEG_QUALITY,
  0.75,
  0.5,
  0.9,
)
const DETECTION_GRACE_PERIOD_MS = boundedNumber(
  import.meta.env.VITE_DETECTION_GRACE_PERIOD_MS,
  FRAME_CAPTURE_INTERVAL_MS * 2 + 1000,
  1000,
  30000,
)
const FEATURE_LABELS = {
  person_detection: 'Person detection',
  result_persistence: 'Detection summary persistence',
  face_detection: 'Face detection',
  face_recognition: 'Student identity recognition',
  tracking: 'Tracking',
  attention_estimation: 'Attention estimation',
  attendance: 'Attendance persistence',
}

function captureJpegFrame(video) {
  const scale = Math.min(
    1,
    FRAME_CAPTURE_MAX_EDGE / video.videoWidth,
    FRAME_CAPTURE_MAX_EDGE / video.videoHeight,
  )
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(1, Math.round(video.videoWidth * scale))
  canvas.height = Math.max(1, Math.round(video.videoHeight * scale))

  const context = canvas.getContext('2d')
  if (!context) {
    return Promise.reject(
      new Error('This browser could not prepare a camera frame for analysis.'),
    )
  }

  context.drawImage(video, 0, 0, canvas.width, canvas.height)
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) {
          resolve(blob)
        } else {
          reject(new Error('The camera frame could not be encoded as JPEG.'))
        }
      },
      'image/jpeg',
      FRAME_JPEG_QUALITY,
    )
  })
}

function getCameraErrorMessage(error) {
  switch (error?.name) {
    case 'NotAllowedError':
    case 'PermissionDeniedError':
    case 'SecurityError':
      return 'Camera permission was denied or blocked. Allow camera access in your browser settings, then retry. Camera access requires HTTPS or localhost.'
    case 'NotFoundError':
    case 'DevicesNotFoundError':
      return 'No camera is available. Connect a camera and retry.'
    case 'NotReadableError':
    case 'TrackStartError':
      return 'The camera could not be started. It may be in use by another application; close other camera apps and retry.'
    case 'OverconstrainedError':
      return 'The selected camera is no longer available. Choose another camera and retry.'
    case 'AbortError':
      return 'The camera request was interrupted. Retry when the camera is ready.'
    default:
      return 'The camera could not be started. Check browser permissions and device availability, then retry.'
  }
}

function getCameraStatus(cameraState, playbackState) {
  if (cameraState === 'requesting') {
    return 'Requesting access'
  }
  if (cameraState === 'ready' && playbackState === 'playing') {
    return 'Camera preview active'
  }
  if (cameraState === 'ready') {
    return 'Starting preview'
  }
  if (cameraState === 'error') {
    return 'Camera unavailable'
  }
  return 'Camera access not requested'
}

function StatusPill({
  connected,
  pending,
  connectedLabel,
  pendingLabel,
  disconnectedLabel,
}) {
  const label = pending
    ? pendingLabel
    : connected
      ? connectedLabel
      : disconnectedLabel

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium ${
        pending
          ? 'border-amber-400/20 bg-amber-400/10 text-amber-300'
          : connected
            ? 'border-emerald-400/20 bg-emerald-400/10 text-emerald-300'
            : 'border-red-400/20 bg-red-400/10 text-red-300'
      }`}
      role="status"
    >
      {pending ? (
        <LoaderCircle size={13} className="animate-spin" />
      ) : connected ? (
        <Wifi size={13} />
      ) : (
        <WifiOff size={13} />
      )}
      {label}
    </span>
  )
}

export default function LiveMonitoring() {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const mountedRef = useRef(false)
  const cameraRequestRef = useRef(0)
  const cameraBusyRef = useRef(false)
  const sessionRequestRef = useRef(null)
  const monitoringRequestRef = useRef(null)
  const monitoringBusyRef = useRef(false)
  const frameRequestRef = useRef(null)
  const frameBusyRef = useRef(false)
  const frameRateLimitUntilRef = useRef(0)
  const inferenceRunRef = useRef(0)
  const frameSequenceRef = useRef(0)
  const latestAppliedFrameSequenceRef = useRef(0)

  const [videoDevices, setVideoDevices] = useState([])
  const [selectedDeviceId, setSelectedDeviceId] = useState('')
  const [stream, setStream] = useState(null)
  const [cameraState, setCameraState] = useState('idle')
  const [playbackState, setPlaybackState] = useState('idle')
  const [cameraError, setCameraError] = useState('')

  const [activeSession, setActiveSession] = useState(null)
  const [monitoringSession, setMonitoringSession] = useState(null)
  const [monitoringState, setMonitoringState] = useState('idle')
  const [attachedToExistingSession, setAttachedToExistingSession] =
    useState(false)
  const [backendState, setBackendState] = useState('checking')
  const [sessionError, setSessionError] = useState('')
  const [inferenceState, setInferenceState] = useState('idle')
  const [inferenceError, setInferenceError] = useState('')
  const [frameResult, setFrameResult] = useState(null)
  const [detectionOverlay, setDetectionOverlay] = useState(
    EMPTY_DETECTION_OVERLAY,
  )
  const [inferenceRetry, setInferenceRetry] = useState(0)
  const [notice, setNotice] = useState('')

  const monitoringInProgress =
    monitoringState === 'starting' || monitoringState === 'stopping'
  const cameraReady =
    cameraState === 'ready' &&
    playbackState === 'playing' &&
    streamRef.current?.getVideoTracks().some(
      (track) => track.readyState === 'live' && track.enabled,
    )
  const classroomConfigured =
    Number.isSafeInteger(CLASSROOM_ID) && CLASSROOM_ID > 0

  const refreshActiveSession = useCallback(async () => {
    sessionRequestRef.current?.abort()
    const controller = new AbortController()
    sessionRequestRef.current = controller
    setBackendState('checking')
    setSessionError('')

    try {
      const session = await getActiveSession({ signal: controller.signal })
      if (
        !mountedRef.current ||
        sessionRequestRef.current !== controller
      ) {
        return null
      }

      setActiveSession(session)
      setBackendState('connected')
      return session
    } catch (error) {
      if (error?.code === 'ERR_CANCELED') {
        return null
      }
      if (
        !mountedRef.current ||
        sessionRequestRef.current !== controller
      ) {
        return null
      }

      console.error('Failed to check classroom session status:', error)
      setBackendState('error')
      setSessionError(getSessionErrorMessage(error))
      throw error
    } finally {
      if (sessionRequestRef.current === controller) {
        sessionRequestRef.current = null
      }
    }
  }, [])

  const refreshVideoDevices = useCallback(async () => {
    const mediaDevices = navigator.mediaDevices
    if (!mediaDevices?.enumerateDevices) {
      return null
    }

    try {
      const devices = await mediaDevices.enumerateDevices()
      if (!mountedRef.current) {
        return null
      }
      const cameras = devices.filter(
        (device) => device.kind === 'videoinput',
      )
      setVideoDevices(cameras)
      return cameras
    } catch (error) {
      if (mountedRef.current) {
        console.error('Failed to enumerate camera devices:', error)
        setCameraError(
          'Unable to list camera devices. You can still retry camera access.',
        )
      }
      return null
    }
  }, [])

  const releaseCamera = useCallback((nextState = 'idle', message = '') => {
    cameraRequestRef.current += 1
    cameraBusyRef.current = false
    const currentStream = streamRef.current
    streamRef.current = null

    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    currentStream?.getTracks().forEach((track) => track.stop())

    if (mountedRef.current) {
      setStream(null)
      setCameraState(nextState)
      setPlaybackState('idle')
      setCameraError(message)
    }
  }, [])

  const enableCamera = useCallback(async (requestedDeviceId = '') => {
    if (cameraBusyRef.current) {
      return
    }

    const mediaDevices = navigator.mediaDevices
    if (!mediaDevices?.getUserMedia) {
      const message =
        'This browser does not support camera access. Use a current browser over HTTPS or localhost.'
      setCameraState('error')
      setCameraError(message)
      return
    }

    cameraBusyRef.current = true
    const requestId = ++cameraRequestRef.current
    const previousStream = streamRef.current
    streamRef.current = null
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    previousStream?.getTracks().forEach((track) => track.stop())
    setStream(null)
    setPlaybackState('idle')
    setCameraState('requesting')
    setCameraError('')
    setNotice('')

    const videoConstraints = requestedDeviceId
      ? { deviceId: { exact: requestedDeviceId } }
      : true

    try {
      const cameraStream = await mediaDevices.getUserMedia({
        video: videoConstraints,
        audio: false,
      })

      if (
        !mountedRef.current ||
        requestId !== cameraRequestRef.current
      ) {
        cameraStream.getTracks().forEach((track) => track.stop())
        return
      }

      const videoTrack = cameraStream.getVideoTracks()[0]
      if (!videoTrack || videoTrack.readyState !== 'live') {
        cameraStream.getTracks().forEach((track) => track.stop())
        throw new Error('No live video track was returned by the browser.')
      }

      streamRef.current = cameraStream
      setStream(cameraStream)
      setCameraState('ready')

      const actualDeviceId = videoTrack.getSettings?.().deviceId
      if (actualDeviceId) {
        setSelectedDeviceId(actualDeviceId)
      } else if (requestedDeviceId) {
        setSelectedDeviceId(requestedDeviceId)
      }
      await refreshVideoDevices()
    } catch (error) {
      if (
        mountedRef.current &&
        requestId === cameraRequestRef.current
      ) {
        console.error('Unable to access browser camera:', error)
        setCameraState('error')
        setCameraError(
          error?.message?.startsWith('No live video track')
            ? 'The browser did not provide a live video track. Check the camera and retry.'
            : getCameraErrorMessage(error),
        )
      }
    } finally {
      if (requestId === cameraRequestRef.current) {
        cameraBusyRef.current = false
      }
    }
  }, [refreshVideoDevices])

  const stopMonitoring = useCallback(async ({ confirmStop = true } = {}) => {
    if (
      monitoringBusyRef.current ||
      !monitoringSession?.session_id
    ) {
      return
    }

    if (
      confirmStop &&
      !window.confirm(
        `Stop classroom session ${monitoringSession.session_id}? This ends the persisted session for classroom ${CLASSROOM_ID}.`,
      )
    ) {
      return
    }

    monitoringBusyRef.current = true
    const controller = new AbortController()
    monitoringRequestRef.current = controller
    setMonitoringState('stopping')
    setSessionError('')
    setNotice('')

    try {
      const stopped = await stopSession(monitoringSession.session_id, {
        signal: controller.signal,
      })
      if (!mountedRef.current) {
        return
      }

      setActiveSession(null)
      setMonitoringSession(stopped)
      setMonitoringState('idle')
      setAttachedToExistingSession(false)
      setNotice(
        `Session ${stopped.session_id} was stopped. The camera has been released.`,
      )
      notifyClassroomDataChanged()
      releaseCamera()
    } catch (error) {
      if (error?.code === 'ERR_CANCELED') {
        return
      }
      if (mountedRef.current) {
        console.error('Failed to stop classroom monitoring session:', error)
        setSessionError(getSessionErrorMessage(error, 'stop'))
        setMonitoringState('error')
        if (
          error?.response?.status === 404 ||
          error?.response?.status === 409
        ) {
          try {
            const currentSession = await refreshActiveSession()
            if (mountedRef.current) {
              setMonitoringSession(currentSession)
              setAttachedToExistingSession(Boolean(currentSession))
              if (!currentSession) {
                setMonitoringState('idle')
              }
            }
          } catch {
            // The refreshActiveSession call records the API error for the page.
          }
        }
      }
    } finally {
      monitoringBusyRef.current = false
      if (monitoringRequestRef.current === controller) {
        monitoringRequestRef.current = null
      }
    }
  }, [monitoringSession, refreshActiveSession, releaseCamera])

  const startMonitoring = useCallback(async () => {
    if (
      monitoringBusyRef.current ||
      !cameraReady ||
      backendState !== 'connected'
    ) {
      return
    }

    monitoringBusyRef.current = true
    const controller = new AbortController()
    monitoringRequestRef.current = controller
    setMonitoringState('starting')
    setSessionError('')
    setNotice('')

    try {
      let session = await refreshActiveSession()
      let foundExisting = Boolean(session)

      if (!session) {
        try {
          session = await startSession({ signal: controller.signal })
        } catch (startError) {
          if (startError?.response?.status !== 409) {
            throw startError
          }
          session = await refreshActiveSession()
          foundExisting = Boolean(session)
          if (!session) {
            throw startError
          }
        }
      }

      if (
        !mountedRef.current ||
        controller.signal.aborted
      ) {
        return
      }
      if (session.status !== 'ACTIVE') {
        throw new Error(
          'The session service did not return an active classroom session.',
        )
      }

      setActiveSession(session)
      setMonitoringSession(session)
      setAttachedToExistingSession(foundExisting)
      setMonitoringState('active')
      setNotice(
        foundExisting
          ? `Attached to existing session ${session.session_id}. No duplicate session was created.`
          : `Monitoring session ${session.session_id} started.`,
      )
      notifyClassroomDataChanged()
    } catch (error) {
      if (error?.code === 'ERR_CANCELED') {
        return
      }
      if (mountedRef.current) {
        console.error('Failed to start classroom monitoring:', error)
        setMonitoringState('error')
        setSessionError(
          error?.response
            ? getSessionErrorMessage(error, 'start')
            : error?.message ||
                'Unable to start a classroom monitoring session. Please retry.',
        )
      }
    } finally {
      monitoringBusyRef.current = false
      if (monitoringRequestRef.current === controller) {
        monitoringRequestRef.current = null
      }
    }
  }, [backendState, cameraReady, refreshActiveSession])

  useEffect(() => {
    mountedRef.current = true
    const mediaDevices = navigator.mediaDevices
    const onDeviceChange = async () => {
      const cameras = await refreshVideoDevices()
      if (!cameras) {
        return
      }
      const currentStream = streamRef.current
      const currentDeviceId =
        currentStream?.getVideoTracks()[0]?.getSettings?.().deviceId

      if (
        currentStream &&
        currentDeviceId &&
        !cameras.some((device) => device.deviceId === currentDeviceId)
      ) {
        releaseCamera(
          'error',
          'The active camera was disconnected. Connect it again or select another camera.',
        )
        setSelectedDeviceId('')
        setMonitoringState((current) =>
          current === 'active' ? 'error' : current,
        )
      }
    }

    mediaDevices?.addEventListener?.('devicechange', onDeviceChange)
    refreshVideoDevices()
    refreshActiveSession().catch(() => {})

    return () => {
      mountedRef.current = false
      cameraRequestRef.current += 1
      sessionRequestRef.current?.abort()
      monitoringRequestRef.current?.abort()
      const currentStream = streamRef.current
      streamRef.current = null
      currentStream?.getTracks().forEach((track) => track.stop())
      if (videoRef.current) {
        videoRef.current.srcObject = null
      }
      mediaDevices?.removeEventListener?.('devicechange', onDeviceChange)
    }
  }, [refreshActiveSession, refreshVideoDevices, releaseCamera])

  useEffect(() => {
    const sessionId = monitoringSession?.session_id
    if (!sessionId || !classroomConfigured) return undefined

    const controller = new AbortController()
    getMonitoringSummary({
      classroomId: CLASSROOM_ID,
      sessionId,
      signal: controller.signal,
    })
      .then((summary) => {
        if (
          !controller.signal.aborted &&
          summary.classroom_id === CLASSROOM_ID &&
          summary.session_id === sessionId
        ) {
          setFrameResult(summary)
        }
      })
      .catch((error) => {
        if (controller.signal.aborted || error?.code === 'ERR_CANCELED') return
        if (
          error?.response?.status === 404 &&
          error?.response?.data?.detail ===
            'No frame summary exists for this session'
        ) {
          return
        }
        console.error('Failed to load the persisted frame summary:', error)
        setInferenceError(
          error?.response?.data?.detail ||
            getFrameInferenceErrorMessage(error),
        )
      })

    return () => controller.abort()
  }, [classroomConfigured, monitoringSession?.session_id])

  useEffect(() => {
    if (!stream || !videoRef.current) {
      return undefined
    }

    const video = videoRef.current
    let active = true
    const handleTrackEnded = () => {
      if (streamRef.current !== stream) {
        return
      }
      releaseCamera(
        'error',
        'The camera stream ended unexpectedly. Retry camera access to continue.',
      )
      setMonitoringState((current) =>
        current === 'active' ? 'error' : current,
      )
    }

    stream.getVideoTracks().forEach((track) => {
      track.addEventListener('ended', handleTrackEnded)
    })
    video.srcObject = stream
    setPlaybackState('starting')

    video.play().then(
      () => {
        if (active && mountedRef.current && streamRef.current === stream) {
          setPlaybackState('playing')
        }
      },
      (error) => {
        if (active && mountedRef.current && streamRef.current === stream) {
          console.error('Camera preview playback failed:', error)
          setPlaybackState('error')
          setCameraError(
            'The camera is connected but browser video playback failed. Retry camera access or check browser autoplay settings.',
          )
        }
      },
    )

    return () => {
      active = false
      stream.getVideoTracks().forEach((track) => {
        track.removeEventListener('ended', handleTrackEnded)
      })
      if (video.srcObject === stream) {
        video.srcObject = null
      }
    }
  }, [releaseCamera, stream])

  useEffect(() => {
    const sessionId = monitoringSession?.session_id
    if (monitoringState !== 'active' || !cameraReady || !sessionId) {
      setInferenceState(
        monitoringState === 'active' ? 'paused' : 'idle',
      )
      if (monitoringState !== 'active') {
        setFrameResult(null)
        setDetectionOverlay(EMPTY_DETECTION_OVERLAY)
        setInferenceError('')
      }
      return undefined
    }

    const runId = ++inferenceRunRef.current
    frameRateLimitUntilRef.current = 0
    const controller = new AbortController()
    frameRequestRef.current = controller
    let active = true
    setInferenceState('processing')
    setInferenceError('')

    const processFrame = async () => {
      if (
        !active ||
        frameBusyRef.current ||
        Date.now() < frameRateLimitUntilRef.current ||
        controller.signal.aborted
      ) {
        return
      }

      const video = videoRef.current
      if (
        !video ||
        video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA ||
        video.videoWidth < 1 ||
        video.videoHeight < 1
      ) {
        return
      }

      frameBusyRef.current = true
      const requestSequence = ++frameSequenceRef.current
      setInferenceState('processing')
      try {
        const frame = await captureJpegFrame(video)
        if (!active || controller.signal.aborted) {
          return
        }
        const result = await analyzeMonitoringFrame({
          classroomId: CLASSROOM_ID,
          sessionId,
          frame,
          signal: controller.signal,
        })
        if (
          !active ||
          controller.signal.aborted ||
          runId !== inferenceRunRef.current ||
          requestSequence <= latestAppliedFrameSequenceRef.current
        ) {
          return
        }
        if (
          result.session_id !== sessionId ||
          result.classroom_id !== CLASSROOM_ID
        ) {
          throw new Error(
            'The inference response did not match the active classroom session.',
          )
        }
        latestAppliedFrameSequenceRef.current = requestSequence
        setFrameResult(result)
        setDetectionOverlay((current) =>
          updatePersonDetectionOverlay(
            current,
            result,
            requestSequence,
            Date.now(),
            DETECTION_GRACE_PERIOD_MS,
          ),
        )
        setInferenceState('ready')
        setInferenceError('')
      } catch (error) {
        if (
          !active ||
          controller.signal.aborted ||
          error?.code === 'ERR_CANCELED'
        ) {
          return
        }
        console.error('Failed to process a camera frame:', error)
        setInferenceState('error')
        setInferenceError(getFrameInferenceErrorMessage(error))
        const status = error?.response?.status
        if (status === 429) {
          const retryAfter = Number(
            error.response.headers?.['retry-after'],
          )
          if (Number.isFinite(retryAfter) && retryAfter > 0) {
            frameRateLimitUntilRef.current =
              Date.now() + retryAfter * 1000
          }
        }
        if (
          [401, 403, 404, 409, 413, 415, 422, 503, 504].includes(
            status,
          )
        ) {
          setMonitoringState('error')
          if ([404, 409].includes(status)) {
            setActiveSession(null)
            setMonitoringSession(null)
            setAttachedToExistingSession(false)
          }
        }
      } finally {
        frameBusyRef.current = false
      }
    }

    processFrame()
    const interval = window.setInterval(
      processFrame,
      FRAME_CAPTURE_INTERVAL_MS,
    )

    return () => {
      active = false
      window.clearInterval(interval)
      inferenceRunRef.current += 1
      controller.abort()
      if (frameRequestRef.current === controller) {
        frameRequestRef.current = null
      }
    }
  }, [
    cameraReady,
    inferenceRetry,
    monitoringSession?.session_id,
    monitoringState,
  ])

  useEffect(() => {
    const delay = getNextPersonDetectionExpiry(
      detectionOverlay,
      Date.now(),
      DETECTION_GRACE_PERIOD_MS,
    )
    if (delay === null) {
      return undefined
    }

    const timeout = window.setTimeout(() => {
      setDetectionOverlay((current) =>
        expirePersonDetectionOverlay(
          current,
          Date.now(),
          DETECTION_GRACE_PERIOD_MS,
        ),
      )
    }, delay + 1)

    return () => window.clearTimeout(timeout)
  }, [detectionOverlay])

  async function handleSelectCamera(event) {
    const deviceId = event.target.value
    setSelectedDeviceId(deviceId)
    if (streamRef.current && deviceId) {
      await enableCamera(deviceId)
    }
  }

  function handleDisableCamera() {
    releaseCamera()
    setNotice('Camera disabled. No video is being captured or uploaded.')
  }

  async function handleRetry() {
    if (sessionError) {
      try {
        await refreshActiveSession()
      } catch {
        // The API error is surfaced through sessionError.
      }
    }
    if (cameraError) {
      await enableCamera(selectedDeviceId)
    }
    if (inferenceError) {
      setInferenceError('')
      setInferenceRetry((attempt) => attempt + 1)
      if (monitoringSession?.status === 'ACTIVE') {
        setMonitoringState('active')
      }
    }
  }

  const displayedSession = activeSession || monitoringSession
  const monitoringLabel =
    monitoringState === 'starting'
      ? 'Starting session'
      : monitoringState === 'stopping'
        ? 'Stopping session'
        : monitoringState === 'active'
          ? 'Monitoring Session Active — Person Detection Only'
          : monitoringState === 'error'
            ? 'Monitoring needs attention'
            : backendState === 'checking'
              ? 'Checking session status'
              : backendState === 'error'
                ? 'Session status unavailable'
                : activeSession
                ? 'Active classroom session — not attached'
                : monitoringSession?.status === 'COMPLETED'
                  ? 'Monitoring session stopped'
                : 'Monitoring not started'

  return (
    <div className="mx-auto max-w-[1600px] p-4 text-white sm:p-6 lg:p-8">
      <header className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-blue-400">
              Classroom operations
            </span>
            <StatusPill
              connected={backendState === 'connected'}
              pending={backendState === 'checking'}
              connectedLabel="Session API connected"
              pendingLabel="Checking session API"
              disconnectedLabel="Session API unavailable"
            />
          </div>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
            Live Monitoring
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
            Manage the configured classroom session and run person detection
            on periodic, resized camera frames. The authenticated backend
            receives frames only while monitoring is active; it does not store
            images or produce identity, attendance, or attention results.
          </p>
        </div>

        <button
          type="button"
          onClick={() => refreshActiveSession().catch(() => {})}
          disabled={backendState === 'checking'}
          className="inline-flex items-center justify-center gap-2 self-start rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50 lg:self-auto"
        >
          <RefreshCw
            size={16}
            className={backendState === 'checking' ? 'animate-spin' : ''}
          />
          Refresh status
        </button>
      </header>

      <div className="mb-5 grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
        <StatusCard
          icon={<ShieldCheck size={18} />}
          label="Classroom"
          value={classroomConfigured ? `ID ${CLASSROOM_ID}` : 'Not configured'}
          detail={
            classroomConfigured
              ? 'From VITE_DEFAULT_CLASSROOM_ID'
              : 'Configure VITE_DEFAULT_CLASSROOM_ID'
          }
        />
        <StatusCard
          icon={<Camera size={18} />}
          label="Camera"
          value={getCameraStatus(cameraState, playbackState)}
          detail={
            cameraState === 'ready' && playbackState === 'playing'
              ? 'Local browser preview'
              : 'Permission is requested only when you enable the camera'
          }
        />
        <StatusCard
          icon={<Activity size={18} />}
          label="Monitoring session"
          value={monitoringLabel}
          detail={
            attachedToExistingSession
              ? 'Using the existing persisted session'
              : 'Starts person detection only after session activation'
          }
        />
        <StatusCard
          icon={<Activity size={18} />}
          label="Frame inference"
          value={
            inferenceState === 'processing'
              ? 'Processing camera frame'
              : inferenceState === 'ready'
                ? `${frameResult?.detection_count ?? 0} people detected`
                : inferenceState === 'error'
                  ? 'Person detection unavailable'
                  : inferenceState === 'paused'
                    ? 'Waiting for camera and active session'
                    : 'Not started'
          }
          detail={
            inferenceState === 'ready'
              ? `${frameResult.inference_duration_ms.toFixed(1)} ms inference · last processed ${new Date(frameResult.processed_at).toLocaleTimeString()}`
              : 'Authenticated JPEG frames are sent every few seconds while active'
          }
        />
      </div>

      {(sessionError || cameraError || inferenceError) && (
        <div
          className="mb-5 flex flex-col gap-3 rounded-xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-300 sm:flex-row sm:items-start sm:justify-between"
          role="alert"
        >
          <div className="flex items-start gap-3">
            <AlertCircle size={18} className="mt-0.5 shrink-0" />
            <div className="space-y-1">
              {sessionError && <p>{sessionError}</p>}
              {cameraError && <p>{cameraError}</p>}
              {inferenceError && <p>{inferenceError}</p>}
            </div>
          </div>
          <button
            type="button"
            onClick={handleRetry}
            disabled={
              backendState === 'checking' || cameraState === 'requesting'
            }
            className="shrink-0 self-start underline underline-offset-2 hover:text-red-200 disabled:opacity-50"
          >
            Retry
          </button>
        </div>
      )}

      {notice && (
        <div
          className="mb-5 flex items-start gap-3 rounded-xl border border-blue-400/20 bg-blue-500/10 px-4 py-3 text-sm text-blue-200"
          role="status"
        >
          <CheckCircle2 size={18} className="mt-0.5 shrink-0" />
          <p>{notice}</p>
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.7fr)_minmax(300px,0.8fr)]">
        <section className="overflow-hidden rounded-2xl border border-white/10 bg-[#0b1220]">
          <div className="flex flex-col gap-3 border-b border-white/10 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
            <div>
              <h2 className="font-semibold">Camera Preview</h2>
              <p className="mt-1 text-xs text-slate-500">
                Live video from the selected camera, displayed locally.
              </p>
            </div>
            {videoDevices.length > 1 && (
              <label className="flex flex-col gap-1 text-xs text-slate-400 sm:min-w-56">
                Camera device
                <select
                  value={selectedDeviceId}
                  onChange={handleSelectCamera}
                  disabled={
                    cameraState === 'requesting' ||
                    monitoringState === 'active' ||
                    monitoringInProgress
                  }
                  className="rounded-lg border border-white/10 bg-[#101827] px-3 py-2 text-sm text-slate-200 outline-none focus:border-blue-400 disabled:opacity-50"
                >
                  {!selectedDeviceId && (
                    <option value="">Select a camera</option>
                  )}
                  {videoDevices.map((device, index) => (
                    <option key={device.deviceId || index} value={device.deviceId}>
                      {device.label || `Camera ${index + 1}`}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>

          <div className="p-3 sm:p-5">
            <div className="relative flex aspect-video min-h-64 items-center justify-center overflow-hidden rounded-xl border border-white/10 bg-black">
              <video
                ref={videoRef}
                autoPlay
                muted
                playsInline
                aria-label="Live camera preview"
                className={`h-full w-full object-contain ${
                  cameraState === 'ready' ? 'block' : 'hidden'
                }`}
              />
              {cameraState === 'ready' &&
                (detectionOverlay.boxes.length > 0 ||
                  frameResult?.face_detections?.length > 0) && (
                  <svg
                    className="pointer-events-none absolute inset-0 h-full w-full"
                    viewBox={`0 0 ${videoRef.current?.videoWidth || 1} ${videoRef.current?.videoHeight || 1}`}
                    preserveAspectRatio="xMidYMid meet"
                    role="img"
                    aria-label={`Up to ${detectionOverlay.boxes.length} people recently detected; boxes expire after a missed-detection grace period`}
                  >
                    {(frameResult?.face_detections || []).map((face, index) => {
                      const scaleX = (videoRef.current?.videoWidth || 1) / frameResult.frame_width
                      const scaleY = (videoRef.current?.videoHeight || 1) / frameResult.frame_height
                      return (
                        <rect
                          key={`face-${index}-${face.x1}-${face.y1}`}
                          x={face.x1 * scaleX}
                          y={face.y1 * scaleY}
                          width={(face.x2 - face.x1) * scaleX}
                          height={(face.y2 - face.y1) * scaleY}
                          fill="none"
                          stroke="#facc15"
                          strokeWidth="2"
                          vectorEffect="non-scaling-stroke"
                        />
                      )
                    })}
                    {detectionOverlay.boxes.map((box, index) => {
                      const detection = toVideoCoordinates(
                        box,
                        videoRef.current?.videoWidth || 1,
                        videoRef.current?.videoHeight || 1,
                      )
                      const age = Date.now() - box.lastSeenAt
                      const opacity = Math.max(
                        0.25,
                        1 - age / DETECTION_GRACE_PERIOD_MS,
                      )
                      return (
                        <g
                          key={`${index}-${box.lastSeenAt}-${box.x1}-${box.y1}`}
                          opacity={opacity}
                        >
                          <rect
                            x={detection.x1}
                            y={detection.y1}
                            width={detection.x2 - detection.x1}
                            height={detection.y2 - detection.y1}
                            fill="none"
                            stroke="#4ade80"
                            strokeWidth="3"
                            vectorEffect="non-scaling-stroke"
                          />
                          <text
                            x={detection.x1 + 4}
                            y={Math.max(16, detection.y1 + 18)}
                            fill="#dcfce7"
                            stroke="#052e16"
                            strokeWidth="3"
                            paintOrder="stroke"
                            fontSize="16"
                          >
                            Person {box.trackId ? `#${box.trackId} · ` : ''}
                            {(box.confidence * 100).toFixed(1)}%
                          </text>
                        </g>
                      )
                    })}
                  </svg>
                )}
              {cameraState !== 'ready' && (
                <div className="mx-auto flex max-w-sm flex-col items-center px-6 text-center">
                  {cameraState === 'requesting' ? (
                    <LoaderCircle
                      size={36}
                      className="mb-4 animate-spin text-blue-400"
                    />
                  ) : cameraState === 'error' ? (
                    <CameraOff size={36} className="mb-4 text-red-300" />
                  ) : (
                    <Camera size={36} className="mb-4 text-slate-500" />
                  )}
                  <p className="font-medium text-slate-200">
                    {cameraState === 'requesting'
                      ? 'Waiting for camera permission...'
                      : cameraState === 'error'
                        ? 'Camera preview unavailable'
                        : 'Camera is off'}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-slate-500">
                    {cameraState === 'idle'
                      ? 'Enable the camera to show its live feed here. Frames are sent only after you start monitoring.'
                      : cameraState === 'requesting'
                        ? 'Choose Allow in the browser permission prompt to continue.'
                        : 'Resolve the camera issue and use Retry Camera.'}
                  </p>
                </div>
              )}
              {cameraState === 'ready' && playbackState === 'starting' && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/70 text-sm text-slate-200">
                  <LoaderCircle size={16} className="mr-2 animate-spin" />
                  Starting video preview...
                </div>
              )}
              {cameraState === 'ready' && playbackState === 'error' && (
                <div className="absolute inset-x-4 bottom-4 rounded-lg border border-amber-400/20 bg-black/80 p-3 text-sm text-amber-200">
                  Video playback failed. Retry camera access to continue.
                </div>
              )}
            </div>

            <div className="mt-4 flex flex-wrap gap-3">
              {cameraState !== 'ready' ? (
                <button
                  type="button"
                  onClick={() => enableCamera(selectedDeviceId)}
                  disabled={
                    cameraState === 'requesting' ||
                    monitoringState === 'active' ||
                    monitoringInProgress
                  }
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {cameraState === 'requesting' ? (
                    <LoaderCircle size={16} className="animate-spin" />
                  ) : cameraState === 'error' ? (
                    <RefreshCw size={16} />
                  ) : (
                    <Camera size={16} />
                  )}
                  {cameraState === 'requesting'
                    ? 'Requesting Camera...'
                    : cameraState === 'error'
                      ? 'Retry Camera'
                      : 'Enable Camera'}
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleDisableCamera}
                  disabled={
                    monitoringState === 'active' ||
                    monitoringInProgress ||
                    (monitoringState === 'error' &&
                      monitoringSession?.status === 'ACTIVE')
                  }
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <CameraOff size={16} />
                  Disable Camera
                </button>
              )}
              {monitoringState !== 'active' && (
                <button
                  type="button"
                  onClick={startMonitoring}
                  disabled={
                    !cameraReady ||
                    backendState !== 'connected' ||
                    monitoringInProgress ||
                    monitoringState === 'active' ||
                    !classroomConfigured
                  }
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-emerald-400/20 bg-emerald-500/10 px-4 py-2.5 text-sm font-semibold text-emerald-200 transition hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {monitoringState === 'starting' ? (
                    <LoaderCircle size={16} className="animate-spin" />
                  ) : (
                    <Play size={16} />
                  )}
                  {monitoringState === 'starting'
                    ? 'Starting Monitoring...'
                    : monitoringState === 'error' &&
                        monitoringSession?.status === 'ACTIVE'
                      ? 'Reconnect Monitoring'
                      : 'Start Monitoring'}
                </button>
              )}
              {(monitoringState === 'active' ||
                (monitoringState === 'error' &&
                  monitoringSession?.status === 'ACTIVE')) && (
                <button
                  type="button"
                  onClick={() => stopMonitoring()}
                  disabled={monitoringInProgress}
                  className="inline-flex items-center justify-center gap-2 rounded-xl border border-red-400/20 bg-red-500/10 px-4 py-2.5 text-sm font-semibold text-red-200 transition hover:bg-red-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {monitoringState === 'stopping' ? (
                    <LoaderCircle size={16} className="animate-spin" />
                  ) : (
                    <Square size={14} />
                  )}
                  {monitoringState === 'stopping'
                    ? 'Stopping Monitoring...'
                    : 'Stop Monitoring'}
                </button>
              )}
              <button
                type="button"
                onClick={() => refreshVideoDevices()}
                disabled={cameraState === 'requesting'}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <RefreshCw size={16} />
                Refresh Cameras
              </button>
            </div>

            <p className="mt-4 flex items-start gap-2 text-xs leading-5 text-slate-500">
              <CircleHelp size={15} className="mt-0.5 shrink-0" />
              Camera permission is requested only after you click Enable Camera.
              While monitoring is active, resized JPEG frames are sent to the
              authenticated backend for person detection; the frames are not
              recorded or persisted. Access generally requires HTTPS or
              localhost.
            </p>
          </div>
        </section>

        <aside className="space-y-5">
          <section className="rounded-2xl border border-white/10 bg-[#0b1220] p-5">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/10 text-blue-300">
                <Activity size={19} />
              </div>
              <div>
                <h2 className="font-semibold">Classroom Session</h2>
                <p className="mt-1 text-xs text-slate-500">
                  Authorized teacher session for the configured classroom.
                </p>
              </div>
            </div>

            <div className="mt-5 space-y-3 rounded-xl border border-white/5 bg-white/[0.02] p-4">
              <SessionDetail
                label="Session ID"
                value={displayedSession?.session_id || 'No session loaded'}
              />
              <SessionDetail
                label="Persisted status"
                value={displayedSession?.status || '—'}
              />
              <SessionDetail
                label="Started"
                value={
                  displayedSession?.started_at
                    ? new Date(displayedSession.started_at).toLocaleString()
                    : '—'
                }
              />
            </div>

            {activeSession && monitoringState !== 'active' && (
              <p className="mt-3 rounded-lg border border-amber-400/20 bg-amber-500/5 px-3 py-2 text-xs leading-5 text-amber-200">
                An active session already exists. Start Monitoring will attach
                to it instead of creating a duplicate. Stopping monitoring will
                stop that persisted session.
              </p>
            )}
            {monitoringState === 'active' && (
              <p className="mt-3 rounded-lg border border-blue-400/20 bg-blue-500/5 px-3 py-2 text-xs leading-5 text-blue-200">
                This session is connected to backend person detection. It
                detects people in the latest sampled frame only; student identity,
                attention, attendance, alerts, and analytics are not inferred.
              </p>
            )}
          </section>

          <section className="rounded-2xl border border-white/10 bg-[#0b1220] p-5">
            <div className="flex items-start gap-3">
              <Activity size={18} className="mt-0.5 shrink-0 text-blue-300" />
              <div>
                <h2 className="text-sm font-semibold text-slate-100">
                  Latest person-detection frame
                </h2>
                <p className="mt-2 text-xs leading-5 text-slate-400">
                  {frameResult
                    ? `${frameResult.detection_count} person${
                        frameResult.detection_count === 1 ? '' : 's'
                      } detected at ${new Date(
                        frameResult.processed_at,
                      ).toLocaleTimeString()} after receipt at ${new Date(
                        frameResult.frame_received_at,
                      ).toLocaleTimeString()} (${frameResult.inference_duration_ms.toFixed(
                        1,
                      )} ms inference). These are person detections, not student identities.`
                    : inferenceState === 'processing'
                      ? 'Waiting for the first backend inference result.'
                      : 'No frame has been processed in this monitoring session.'}
                </p>
                {frameResult?.detections?.length > 0 && (
                  <ul className="mt-3 space-y-1 text-xs text-slate-300">
                    {frameResult.detections.slice(0, 5).map(
                      (detection, index) => (
                        <li key={`${index}-${detection.x1}-${detection.y1}`}>
                          Detection {index + 1} · person · detector confidence{' '}
                          {(detection.confidence * 100).toFixed(1)}% · track #{detection.track_id}
                        </li>
                      ),
                    )}
                    {frameResult.detection_count > 5 && (
                      <li>
                        {frameResult.detection_count - 5} more person detections
                      </li>
                    )}
                  </ul>
                )}
                {frameResult?.face_detections?.length > 0 && (
                  <p className="mt-2 text-xs text-yellow-200">
                    {frameResult.face_detections.length} face box(es) detected independently; identity is unavailable and Haar confidence is unscored.
                  </p>
                )}
                {detectionOverlay.boxes.length > 0 && (
                  <p className="mt-2 text-xs text-emerald-200/80">
                    Overlay boxes are from recent real detections and fade out
                    after {DETECTION_GRACE_PERIOD_MS / 1000} seconds without a
                    matching detection.
                  </p>
                )}
                {frameResult && (
                  <>
                    <p className="mt-3 text-xs text-slate-500">
                      {frameResult.results_persisted
                        ? 'Latest bounding boxes and frame metadata were saved in a bounded session summary. Raw images are not stored.'
                        : 'Detection succeeded, but the session summary could not be saved. Check backend logs for the database error and confirm the frame-summary migration has been applied.'}{' '}
                      Other capability status:
                    </p>
                    <ul className="mt-2 space-y-2">
                      {Object.entries(frameResult.features).map(
                        ([feature, result]) => (
                          <li
                            key={feature}
                            className="flex flex-col gap-0.5 sm:flex-row sm:justify-between sm:gap-3"
                          >
                            <span className="text-xs text-slate-300">
                              {FEATURE_LABELS[feature]}
                            </span>
                            <span
                              className={`text-xs ${
                                result.status === 'available'
                                  ? 'text-emerald-300'
                                  : result.status === 'error'
                                    ? 'text-rose-300'
                                    : 'text-amber-200'
                              }`}
                              title={result.detail}
                            >
                              {result.status === 'available'
                                ? 'Available for this response'
                                : result.status === 'error'
                                  ? 'Failed for this response'
                                  : 'Not connected'}
                            </span>
                            {result.status === 'error' && (
                              <span className="text-xs text-rose-200/80 sm:max-w-[60%] sm:text-right">
                                {result.detail}
                              </span>
                            )}
                          </li>
                        ),
                      )}
                    </ul>
                  </>
                )}
                <p className="mt-3 text-xs leading-5 text-slate-500">
                  Leaving this page releases the camera but does not end the
                  persisted classroom session. Stop it before leaving or use
                  Session Control to end it later.
                </p>
              </div>
            </div>
          </section>
        </aside>
      </div>
    </div>
  )
}

function StatusCard({ icon, label, value, detail }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-[#0b1220] p-4 sm:p-5">
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-blue-500/10 text-blue-300">
          {icon}
        </div>
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
            {label}
          </p>
          <p className="mt-1 break-words text-sm font-semibold text-slate-100">
            {value}
          </p>
          <p className="mt-1 text-xs text-slate-500">{detail}</p>
        </div>
      </div>
    </div>
  )
}

function SessionDetail({ label, value }) {
  return (
    <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between sm:gap-3">
      <span className="shrink-0 text-xs text-slate-500">{label}</span>
      <span className="break-all text-right text-xs font-medium text-slate-200">
        {value}
      </span>
    </div>
  )
}
