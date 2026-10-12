import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock3,
  History,
  Play,
  RefreshCw,
  Square,
  Timer,
  Users,
  Wifi,
  WifiOff,
} from 'lucide-react'

import {
  CLASSROOM_ID,
  getActiveSession,
  getSessionErrorMessage,
  getSessions,
  startSession,
  stopSession,
} from '../services/sessionControlService'

const STATUS = {
  ACTIVE: 'ACTIVE',
  COMPLETED: 'COMPLETED',
  INTERRUPTED: 'INTERRUPTED',
}
const HISTORY_PAGE_SIZE = 100

function formatDateTime(value) {
  if (!value) {
    return '—'
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return '—'
  }

  return date.toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function formatDuration(seconds) {
  if (
    seconds === null ||
    seconds === undefined ||
    !Number.isFinite(Number(seconds))
  ) {
    return '—'
  }

  const totalSeconds = Math.floor(Math.max(0, Number(seconds)))

  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor(
    (totalSeconds % 3600) / 60,
  )
  const remainingSeconds = totalSeconds % 60

  if (hours > 0) {
    return `${hours}h ${minutes}m`
  }

  if (minutes > 0) {
    return `${minutes}m ${remainingSeconds}s`
  }

  return `${remainingSeconds}s`
}

function getStatusClasses(status) {
  if (status === STATUS.ACTIVE) {
    return 'border-emerald-400/20 bg-emerald-400/10 text-emerald-300'
  }

  if (status === STATUS.COMPLETED) {
    return 'border-cyan-400/20 bg-cyan-400/10 text-cyan-300'
  }

  if (status === STATUS.INTERRUPTED) {
    return 'border-amber-400/20 bg-amber-400/10 text-amber-300'
  }

  return 'border-white/10 bg-white/5 text-slate-400'
}

function getStatusIcon(status) {
  if (status === STATUS.ACTIVE) {
    return <Activity size={14} />
  }

  if (status === STATUS.COMPLETED) {
    return <CheckCircle2 size={14} />
  }

  return <Clock3 size={14} />
}

export default function SessionControl() {
  const [sessions, setSessions] = useState([])
  const [historyOffset, setHistoryOffset] = useState(0)
  const [hasMoreHistory, setHasMoreHistory] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [activeSession, setActiveSession] = useState(null)

  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [backendConnected, setBackendConnected] = useState(false)
  const [sessionState, setSessionState] = useState('loading')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const mountedRef = useRef(false)
  const activeRequestRef = useRef(null)
  const actionRequestRef = useRef(null)
  const historyRequestRef = useRef(null)
  const actionInProgressRef = useRef(false)
  const requestVersionRef = useRef(0)

  const loadSessions = useCallback(async ({ showLoader = true } = {}) => {
    activeRequestRef.current?.abort()
    historyRequestRef.current?.abort()
    historyRequestRef.current = null
    const controller = new AbortController()
    activeRequestRef.current = controller
    const requestVersion = ++requestVersionRef.current

    if (showLoader) {
      setLoading(true)
    }
    setError('')
    setSessionState('loading')

    try {
      const [sessionHistory, active] = await Promise.all([
        getSessions({
          limit: HISTORY_PAGE_SIZE,
          signal: controller.signal,
        }),
        getActiveSession({ signal: controller.signal }),
      ])

      if (
        !mountedRef.current ||
        requestVersion !== requestVersionRef.current
      ) {
        return
      }

      setSessions(sessionHistory)
      setHistoryOffset(sessionHistory.length)
      setHasMoreHistory(sessionHistory.length === HISTORY_PAGE_SIZE)
      setActiveSession(active)
      setBackendConnected(true)
      setSessionState('loaded')
    } catch (requestError) {
      if (requestError.code === 'ERR_CANCELED') {
        return
      }

      console.error(
        'Failed to load classroom sessions:',
        requestError,
      )

      if (
        mountedRef.current &&
        requestVersion === requestVersionRef.current
      ) {
        setBackendConnected(false)
        setSessionState('error')
        setError(getSessionErrorMessage(requestError))
      }
    } finally {
      if (
        mountedRef.current &&
        requestVersion === requestVersionRef.current
      ) {
        setLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    loadSessions()

    return () => {
      mountedRef.current = false
      activeRequestRef.current?.abort()
      actionRequestRef.current?.abort()
      historyRequestRef.current?.abort()
    }
  }, [loadSessions])

  const loadMoreHistory = async () => {
    if (
      historyLoading ||
      historyRequestRef.current ||
      !hasMoreHistory
    ) {
      return
    }

    const controller = new AbortController()
    historyRequestRef.current = controller
    setHistoryLoading(true)
    setError('')

    try {
      const nextPage = await getSessions({
        limit: HISTORY_PAGE_SIZE,
        offset: historyOffset,
        signal: controller.signal,
      })

      if (
        !mountedRef.current ||
        historyRequestRef.current !== controller
      ) {
        return
      }

      setSessions((current) => {
        const existingIds = new Set(
          current.map((session) => session.session_id),
        )
        return [
          ...current,
          ...nextPage.filter(
            (session) => !existingIds.has(session.session_id),
          ),
        ]
      })
      setHistoryOffset((current) => current + nextPage.length)
      setHasMoreHistory(nextPage.length === HISTORY_PAGE_SIZE)
    } catch (requestError) {
      if (requestError.code !== 'ERR_CANCELED' && mountedRef.current) {
        console.error('Failed to load more classroom sessions:', requestError)
        setError(getSessionErrorMessage(requestError))
      }
    } finally {
      if (mountedRef.current) {
        setHistoryLoading(false)
      }
      if (historyRequestRef.current === controller) {
        historyRequestRef.current = null
      }
    }
  }

  const completedHistory = useMemo(() => {
    return sessions.filter(
      (session) =>
        session.status === STATUS.COMPLETED ||
        session.status === STATUS.INTERRUPTED,
    )
  }, [sessions])

  const handleStartSession = async () => {
    if (actionInProgressRef.current || sessionState !== 'loaded') {
      return
    }

    if (activeSession) {
      setError(
        'An active classroom session already exists. Stop it before starting a new one.',
      )
      return
    }

    actionInProgressRef.current = true
    const controller = new AbortController()
    actionRequestRef.current = controller
    setActionLoading(true)
    setError('')
    setSuccess('')

    try {
      const newSession = await startSession({ signal: controller.signal })
      if (!mountedRef.current) {
        return
      }

      setActiveSession(newSession)
      setSessions((current) => [
        newSession,
        ...current.filter(
          (session) =>
            session.session_id !== newSession.session_id,
        ),
      ])

      setBackendConnected(true)
      setSuccess(
        `Session ${newSession.session_id} started successfully.`,
      )
      await loadSessions({ showLoader: false })
    } catch (requestError) {
      if (requestError.code === 'ERR_CANCELED') {
        return
      }

      console.error(
        'Failed to start classroom session:',
        requestError,
      )

      if (mountedRef.current) {
        const message = getSessionErrorMessage(requestError, 'start')
        if (requestError.response?.status === 409) {
          await loadSessions({ showLoader: false })
        }
        if (mountedRef.current) {
          setError(message)
        }
      }
    } finally {
      actionInProgressRef.current = false
      if (mountedRef.current) {
        setActionLoading(false)
      }
    }
  }

  const handleStopSession = async (session) => {
    if (actionInProgressRef.current) {
      return
    }

    if (!session?.session_id) {
      setError('Unable to stop session: session ID is missing.')
      return
    }

    const confirmed = window.confirm(
      `Stop classroom session ${session.session_id}?`,
    )

    if (!confirmed) {
      return
    }

    actionInProgressRef.current = true
    const controller = new AbortController()
    actionRequestRef.current = controller
    setActionLoading(true)
    setError('')
    setSuccess('')

    try {
      const stoppedSession = await stopSession(session.session_id, {
        signal: controller.signal,
      })
      if (!mountedRef.current) {
        return
      }

      setActiveSession(null)
      setSessions((current) => [
        stoppedSession,
        ...current.filter(
          (item) => item.session_id !== stoppedSession.session_id,
        ),
      ])
      setBackendConnected(true)
      setSuccess(
        `Session ${session.session_id} stopped successfully.`,
      )
      await loadSessions({ showLoader: false })
    } catch (requestError) {
      if (requestError.code === 'ERR_CANCELED') {
        return
      }

      console.error(
        'Failed to stop classroom session:',
        requestError,
      )

      if (mountedRef.current) {
        const message = getSessionErrorMessage(requestError, 'stop')
        if ([404, 409].includes(requestError.response?.status)) {
          await loadSessions({ showLoader: false })
        }
        if (mountedRef.current) {
          setError(message)
        }
      }
    } finally {
      actionInProgressRef.current = false
      if (mountedRef.current) {
        setActionLoading(false)
      }
    }
  }

  const handleRefresh = async () => {
    setSuccess('')
    await loadSessions()
  }

  return (
    <div className="min-h-screen bg-[#070b16] px-4 py-6 text-white sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">

        {/* Header */}
        <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-2">
              <span className="text-sm font-medium text-blue-400">
                Classroom operations
              </span>

              <span
                className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${
                  backendConnected
                    ? 'border-emerald-400/20 bg-emerald-400/10 text-emerald-300'
                    : 'border-red-400/20 bg-red-400/10 text-red-300'
                }`}
              >
                {backendConnected ? (
                  <>
                    <Wifi size={12} />
                    Backend connected
                  </>
                ) : (
                  <>
                    <WifiOff size={12} />
                    {sessionState === 'loading'
                      ? 'Checking backend'
                      : 'Backend unavailable'}
                  </>
                )}
              </span>
            </div>

            <h1 className="text-3xl font-bold tracking-tight">
              Session Control
            </h1>

            <p className="mt-2 max-w-2xl text-sm text-slate-400">
              Start, monitor, and stop classroom sessions
              without directly changing the database.
            </p>
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleRefresh}
              disabled={loading || actionLoading}
              className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <RefreshCw
                size={16}
                className={
                  loading ? 'animate-spin' : ''
                }
              />
              Refresh
            </button>

            <button
              type="button"
              onClick={handleStartSession}
              disabled={
                Boolean(activeSession) ||
                loading ||
                actionLoading ||
                sessionState !== 'loaded' ||
                !Number.isSafeInteger(CLASSROOM_ID) ||
                CLASSROOM_ID < 1
              }
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Play size={16} />
              {actionLoading
                ? 'Processing...'
                : 'Start Session'}
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-5 flex items-start gap-3 rounded-xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            <AlertCircle
              size={18}
              className="mt-0.5 shrink-0"
            />

            <div className="flex flex-1 items-center justify-between gap-3">
              <span>{error}</span>
              {sessionState === 'error' && (
                <button
                  type="button"
                  onClick={handleRefresh}
                  disabled={loading || actionLoading}
                  className="shrink-0 underline underline-offset-2 hover:text-red-200 disabled:opacity-50"
                >
                  Retry
                </button>
              )}
            </div>
          </div>
        )}

        {/* Success */}
        {success && (
          <div className="mb-5 flex items-start gap-3 rounded-xl border border-emerald-400/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
            <CheckCircle2
              size={18}
              className="mt-0.5 shrink-0"
            />

            <div>{success}</div>
          </div>
        )}

        {/* Active session warning */}
        {activeSession && (
          <div className="mb-5 flex items-start gap-3 rounded-xl border border-amber-400/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-300">
            <AlertCircle
              size={18}
              className="mt-0.5 shrink-0"
            />

            <div>
              An active classroom session already exists.
              Stop the active session before starting a new
              one.
            </div>
          </div>
        )}

        {/* Metrics */}
        <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">

          <MetricCard
            icon={<Activity size={18} />}
            label="Active Sessions"
            value={
              sessionState === 'loaded'
                ? activeSession
                  ? '1'
                  : '0'
                : '—'
            }
            description={
              sessionState !== 'loaded'
                ? 'Status unavailable'
                : activeSession
                ? 'Currently active'
                : 'No active session'
            }
          />

          <MetricCard
            icon={<History size={18} />}
            label="Completed History"
            value={
              sessionState === 'loaded'
                ? completedHistory.length
                : '—'
            }
            description="Completed or interrupted"
          />

          <MetricCard
            icon={<Timer size={18} />}
            label="Latest Session"
            value={
              sessionState === 'loaded' && sessions[0]?.session_id
                ? sessions[0].session_id.length > 20
                  ? `${sessions[0].session_id.slice(0, 20)}...`
                  : sessions[0].session_id
                : '—'
            }
            description={
              sessionState !== 'loaded'
                ? 'Status unavailable'
                : sessions[0]?.status || 'No sessions'
            }
          />

          <MetricCard
            icon={<Users size={18} />}
            label="Classroom"
            value={
              Number.isSafeInteger(CLASSROOM_ID) && CLASSROOM_ID > 0
                ? `ID ${CLASSROOM_ID}`
                : 'Not configured'
            }
            description="Configured classroom"
          />
        </div>

        {/* Active Session */}
        <section className="mb-6 overflow-hidden rounded-2xl border border-white/10 bg-[#0b1220]">

          <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
            <div>
              <div className="flex items-center gap-2">
                <Activity
                  size={18}
                  className="text-emerald-400"
                />

                <h2 className="font-semibold">
                  Active Classroom Session
                </h2>
              </div>

              <p className="mt-1 text-xs text-slate-500">
                Current session reported by the classroom
                session service.
              </p>
            </div>

            <span className="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-400">
              {sessionState === 'loaded'
                ? activeSession
                  ? '1 active'
                  : '0 active'
                : 'Status unavailable'}
            </span>
          </div>

          {sessionState === 'loading' ? (
            <div className="flex items-center justify-center px-5 py-10 text-sm text-slate-400">
              <RefreshCw size={16} className="mr-2 animate-spin" />
              Checking active session...
            </div>
          ) : sessionState === 'error' ? (
            <div className="px-5 py-10 text-center text-sm text-slate-400">
              Active session status is unavailable. Retry the session request.
            </div>
          ) : activeSession ? (
            <div className="flex flex-col gap-4 px-5 py-5 lg:flex-row lg:items-center lg:justify-between">

              <div className="flex items-center gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400">
                  <Activity size={20} />
                </div>

                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold">
                      {activeSession.session_id}
                    </span>

                    <StatusBadge
                      status={activeSession.status}
                    />
                  </div>

                  <div className="mt-1 flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-500">
                    <span>
                      Started:{' '}
                      {formatDateTime(
                        activeSession.started_at,
                      )}
                    </span>

                    <span>
                      Created:{' '}
                      {formatDateTime(
                        activeSession.created_at,
                      )}
                    </span>
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={() =>
                  handleStopSession(activeSession)
                }
                disabled={actionLoading}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-red-400/20 bg-red-500/10 px-4 py-2.5 text-sm font-medium text-red-300 transition hover:bg-red-500/20 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Square size={14} />
                Stop Session
              </button>
            </div>
          ) : (
            <div className="px-5 py-10 text-center">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-white/5 text-slate-500">
                <Timer size={22} />
              </div>

              <p className="font-medium text-slate-300">
                No active classroom session
              </p>

              <p className="mt-1 text-sm text-slate-500">
                Start a new session when the classroom is
                ready.
              </p>
            </div>
          )}
        </section>

        {/* History */}
        <section className="overflow-hidden rounded-2xl border border-white/10 bg-[#0b1220]">

          <div className="border-b border-white/10 px-5 py-4">
            <div className="flex items-center gap-2">
              <History
                size={18}
                className="text-blue-400"
              />

              <h2 className="font-semibold">
                Session History
              </h2>
            </div>

            <p className="mt-1 text-xs text-slate-500">
              Persisted sessions, newest first. Load older records
              when needed.
            </p>
          </div>

          {loading ? (
            <div className="flex items-center justify-center px-5 py-12 text-sm text-slate-400">
              <RefreshCw
                size={16}
                className="mr-2 animate-spin"
              />
              Loading session history...
            </div>
          ) : sessionState === 'error' ? (
            <div className="px-5 py-12 text-center text-sm text-slate-400">
              Session history is unavailable. Retry to load the persisted history.
            </div>
          ) : sessions.length === 0 ? (
            <div className="px-5 py-12 text-center text-sm text-slate-500">
              No classroom sessions found.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[800px]">
                <thead>
                  <tr className="border-b border-white/10 text-left text-[11px] uppercase tracking-wider text-slate-500">
                    <th className="px-5 py-4 font-medium">
                      Session
                    </th>

                    <th className="px-5 py-4 font-medium">
                      Status
                    </th>

                    <th className="px-5 py-4 font-medium">
                      Started
                    </th>

                    <th className="px-5 py-4 font-medium">
                      Ended
                    </th>

                    <th className="px-5 py-4 font-medium">
                      Duration
                    </th>

                    <th className="px-5 py-4 text-right font-medium">
                      Action
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {sessions.map((session) => (
                    <tr
                      key={session.session_id}
                      className="border-b border-white/5 last:border-0"
                    >
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-3">
                          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/5 text-slate-400">
                            <Clock3 size={15} />
                          </div>

                          <div>
                            <div className="font-medium text-slate-200">
                              {session.session_id}
                            </div>

                            <div className="text-xs text-slate-600">
                              ID #{session.id}
                            </div>
                          </div>
                        </div>
                      </td>

                      <td className="px-5 py-4">
                        <StatusBadge
                          status={session.status}
                        />
                      </td>

                      <td className="px-5 py-4 text-sm text-slate-400">
                        {formatDateTime(
                          session.started_at,
                        )}
                      </td>

                      <td className="px-5 py-4 text-sm text-slate-400">
                        {formatDateTime(
                          session.ended_at,
                        )}
                      </td>

                      <td className="px-5 py-4 text-sm text-slate-400">
                        {formatDuration(
                          session.duration_seconds,
                        )}
                      </td>

                      <td className="px-5 py-4 text-right">
                        {session.status ===
                          STATUS.ACTIVE && (
                          <button
                            type="button"
                            onClick={() =>
                              handleStopSession(session)
                            }
                            disabled={actionLoading}
                            className="inline-flex items-center gap-2 rounded-lg border border-red-400/20 bg-red-500/10 px-3 py-2 text-xs font-medium text-red-300 transition hover:bg-red-500/20 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            <Square size={12} />
                            Stop
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {hasMoreHistory && sessionState === 'loaded' && (
            <div className="border-t border-white/10 px-5 py-4 text-center">
              <button
                type="button"
                onClick={loadMoreHistory}
                disabled={historyLoading || actionLoading}
                className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-300 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {historyLoading && (
                  <RefreshCw size={14} className="animate-spin" />
                )}
                {historyLoading ? 'Loading older sessions...' : 'Load older sessions'}
              </button>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

function MetricCard({
  icon,
  label,
  value,
  description,
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-[#0b1220] p-5">
      <div className="mb-4 flex h-9 w-9 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
        {icon}
      </div>

      <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
        {label}
      </p>

      <p className="mt-1 truncate text-xl font-semibold text-slate-100">
        {value}
      </p>

      <p className="mt-1 text-xs text-slate-600">
        {description}
      </p>
    </div>
  )
}

function StatusBadge({ status }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${getStatusClasses(
        status,
      )}`}
    >
      {getStatusIcon(status)}
      {status}
    </span>
  )
}