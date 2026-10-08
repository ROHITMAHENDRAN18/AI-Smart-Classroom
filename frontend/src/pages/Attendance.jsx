import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  CalendarDays,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  RefreshCw,
  Users,
  UserX,
  AlertCircle,
} from 'lucide-react'

import {
  getAttendanceSessions,
  getSessionAttendance,
  normalizeAttendanceRecords,
} from '../services/attendanceService'

export default function Attendance() {
  const [sessions, setSessions] = useState([])
  const [selectedSessionId, setSelectedSessionId] =
    useState('')

  const [records, setRecords] = useState([])

  const [loadingSessions, setLoadingSessions] =
    useState(true)

  const [loadingAttendance, setLoadingAttendance] =
    useState(false)

  const [error, setError] = useState('')

  const loadSessions = useCallback(
    async () => {
      try {
        setLoadingSessions(true)
        setError('')

        const data =
          await getAttendanceSessions()

        setSessions(data)

        setSelectedSessionId(
          (current) => {
            if (
              current &&
              data.some(
                (session) =>
                  session.session_id ===
                  current,
              )
            ) {
              return current
            }

            return data[0]?.session_id || ''
          },
        )
      } catch (requestError) {
        console.error(
          'Failed to load attendance sessions:',
          requestError,
        )

        setError(
          getErrorMessage(
            requestError,
            'Unable to load attendance sessions.',
          ),
        )
      } finally {
        setLoadingSessions(false)
      }
    },
    [],
  )

  const loadAttendance = useCallback(
    async (sessionId) => {
      if (!sessionId) {
        setRecords([])
        return
      }

      try {
        setLoadingAttendance(true)
        setError('')

        const data =
          await getSessionAttendance(
            sessionId,
          )

        setRecords(
          normalizeAttendanceRecords(data),
        )
      } catch (requestError) {
        console.error(
          'Failed to load attendance:',
          requestError,
        )

        setRecords([])

        setError(
          getErrorMessage(
            requestError,
            'Unable to load attendance records.',
          ),
        )
      } finally {
        setLoadingAttendance(false)
      }
    },
    [],
  )

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  useEffect(() => {
    loadAttendance(
      selectedSessionId,
    )
  }, [
    selectedSessionId,
    loadAttendance,
  ])

  const summary = useMemo(() => {
    const present = records.filter(
      (record) =>
        record.status === 'PRESENT',
    ).length

    const absent = records.filter(
      (record) =>
        record.status === 'ABSENT',
    ).length

    const unknown = records.filter(
      (record) =>
        record.status === 'UNKNOWN',
    ).length

    const total = records.length

    const percentage =
      total > 0
        ? (present / total) * 100
        : 0

    return {
      present,
      absent,
      unknown,
      total,
      percentage,
    }
  }, [records])

  const selectedSession = useMemo(
    () =>
      sessions.find(
        (session) =>
          session.session_id ===
          selectedSessionId,
      ) || null,
    [
      sessions,
      selectedSessionId,
    ],
  )

  async function handleRefresh() {
    await loadSessions()

    if (selectedSessionId) {
      await loadAttendance(
        selectedSessionId,
      )
    }
  }

  return (
    <div className="mx-auto max-w-[1600px] p-4 sm:p-6 lg:p-8">
      <header className="mb-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm font-medium text-blue-400">
              <ClipboardCheck size={16} />
              Classroom attendance
            </div>

            <h1 className="mt-2 text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Attendance
            </h1>

            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
              Review student attendance records
              captured during classroom sessions.
            </p>
          </div>

          <button
            type="button"
            onClick={handleRefresh}
            disabled={
              loadingSessions ||
              loadingAttendance
            }
            className="flex items-center justify-center gap-2 rounded-xl border border-slate-800 bg-slate-900/70 px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:border-slate-700 hover:bg-slate-800 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCw
              size={16}
              className={
                loadingSessions ||
                loadingAttendance
                  ? 'animate-spin'
                  : ''
              }
            />

            Refresh
          </button>
        </div>
      </header>

      {error && (
        <div className="mb-5 flex items-start gap-3 rounded-xl border border-red-500/20 bg-red-500/5 p-4">
          <AlertCircle
            size={18}
            className="mt-0.5 shrink-0 text-red-400"
          />

          <div>
            <p className="text-sm font-semibold text-red-300">
              Attendance error
            </p>

            <p className="mt-1 text-xs leading-5 text-red-300/70">
              {error}
            </p>
          </div>
        </div>
      )}

      <section className="surface mb-6 p-5 sm:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end">
          <div className="flex-1">
            <label
              htmlFor="attendance-session"
              className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-500"
            >
              Select classroom session
            </label>

            <select
              id="attendance-session"
              value={selectedSessionId}
              onChange={(event) =>
                setSelectedSessionId(
                  event.target.value,
                )
              }
              disabled={
                loadingSessions ||
                sessions.length === 0
              }
              className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-200 outline-none transition focus:border-blue-500/50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {sessions.length === 0 ? (
                <option value="">
                  No classroom sessions available
                </option>
              ) : (
                sessions.map(
                  (session) => (
                    <option
                      key={
                        session.session_id
                      }
                      value={
                        session.session_id
                      }
                    >
                      {session.session_id} —{' '}
                      {session.status}
                    </option>
                  ),
                )
              )}
            </select>
          </div>

          {selectedSession && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:w-auto">
              <SessionInfo
                icon={
                  <CalendarDays size={15} />
                }
                label="Status"
                value={
                  selectedSession.status ||
                  'UNKNOWN'
                }
              />

              <SessionInfo
                icon={<Clock3 size={15} />}
                label="Started"
                value={formatDateTime(
                  selectedSession.started_at,
                )}
              />

              <SessionInfo
                icon={<Clock3 size={15} />}
                label="Ended"
                value={formatDateTime(
                  selectedSession.ended_at,
                )}
              />

              <SessionInfo
                icon={<Clock3 size={15} />}
                label="Duration"
                value={formatDuration(
                  selectedSession.duration_seconds,
                )}
              />
            </div>
          )}
        </div>
      </section>

      <section className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          icon={<Users size={19} />}
          label="Total Records"
          value={summary.total}
          description="Attendance records"
          iconClass="bg-blue-500/10 text-blue-400"
        />

        <SummaryCard
          icon={
            <CheckCircle2 size={19} />
          }
          label="Present"
          value={summary.present}
          description="Marked present"
          iconClass="bg-emerald-500/10 text-emerald-400"
        />

        <SummaryCard
          icon={<UserX size={19} />}
          label="Absent"
          value={summary.absent}
          description="Marked absent"
          iconClass="bg-red-500/10 text-red-400"
        />

        <SummaryCard
          icon={
            <ClipboardCheck size={19} />
          }
          label="Attendance Rate"
          value={`${summary.percentage.toFixed(
            1,
          )}%`}
          description="Present / total records"
          iconClass="bg-violet-500/10 text-violet-400"
        />
      </section>

      <section className="surface overflow-hidden">
        <div className="flex flex-col gap-3 border-b border-slate-800 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
          <div>
            <h2 className="text-base font-semibold text-white">
              Attendance Records
            </h2>

            <p className="mt-1 text-xs text-slate-500">
              Student attendance for the selected
              classroom session.
            </p>
          </div>

          {selectedSessionId && (
            <span className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-[11px] font-medium text-slate-400">
              {selectedSessionId}
            </span>
          )}
        </div>

        {loadingAttendance ? (
          <LoadingState />
        ) : records.length === 0 ? (
          <EmptyState />
        ) : (
          <AttendanceTable records={records} />
        )}
      </section>
    </div>
  )
}

function SummaryCard({
  icon,
  label,
  value,
  description,
  iconClass,
}) {
  return (
    <div className="surface p-5">
      <div
        className={`flex h-10 w-10 items-center justify-center rounded-xl ${iconClass}`}
      >
        {icon}
      </div>

      <p className="mt-5 text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </p>

      <p className="mt-1 text-2xl font-bold tracking-tight text-white">
        {value}
      </p>

      <p className="mt-1 text-xs text-slate-600">
        {description}
      </p>
    </div>
  )
}

function SessionInfo({
  icon,
  label,
  value,
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-2.5">
      <div className="flex items-center gap-1.5 text-slate-500">
        {icon}

        <span className="text-[10px] font-semibold uppercase tracking-wide">
          {label}
        </span>
      </div>

      <p className="mt-1 text-xs font-medium text-slate-300">
        {value}
      </p>
    </div>
  )
}

function AttendanceTable({
  records,
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px]">
        <thead>
          <tr className="border-b border-slate-800 bg-slate-950/40 text-left">
            <th className="px-5 py-4 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Student
            </th>

            <th className="px-5 py-4 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Status
            </th>

            <th className="px-5 py-4 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Confidence
            </th>

            <th className="px-5 py-4 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Recorded
            </th>
          </tr>
        </thead>

        <tbody>
          {records.map(
            (record, index) => (
              <tr
                key={
                  record.id ??
                  `${record.studentId}-${index}`
                }
                className="border-b border-slate-900 transition hover:bg-slate-900/40"
              >
                <td className="px-5 py-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
                      <Users size={16} />
                    </div>

                    <div>
                      <p className="text-sm font-semibold text-white">
                        {record.studentId}
                      </p>

                      <p className="mt-0.5 text-[11px] text-slate-600">
                        Attendance record
                      </p>
                    </div>
                  </div>
                </td>

                <td className="px-5 py-4">
                  <AttendanceStatus
                    status={record.status}
                  />
                </td>

                <td className="px-5 py-4">
                  <Confidence
                    value={record.confidence}
                  />
                </td>

                <td className="px-5 py-4 text-xs text-slate-400">
                  {formatDateTime(
                    record.recordedAt,
                  )}
                </td>
              </tr>
            ),
          )}
        </tbody>
      </table>
    </div>
  )
}

function AttendanceStatus({
  status,
}) {
  if (status === 'PRESENT') {
    return (
      <span className="attention-badge attention-attentive">
        <CheckCircle2 size={13} />
        PRESENT
      </span>
    )
  }

  if (status === 'ABSENT') {
    return (
      <span className="attention-badge attention-not-attentive">
        <UserX size={13} />
        ABSENT
      </span>
    )
  }

  return (
    <span className="attention-badge attention-unknown">
      <AlertCircle size={13} />
      UNKNOWN
    </span>
  )
}

function Confidence({
  value,
}) {
  if (
    value === null ||
    value === undefined
  ) {
    return (
      <span className="text-xs text-slate-600">
        —
      </span>
    )
  }

  const percentage = Math.max(
    0,
    Math.min(100, Number(value) * 100),
  )

  return (
    <div className="w-32">
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-500">
          Match
        </span>

        <span className="text-xs font-semibold text-white">
          {percentage.toFixed(1)}%
        </span>
      </div>

      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-blue-400 transition-all duration-500"
          style={{
            width: `${percentage}%`,
          }}
        />
      </div>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="flex min-h-[280px] items-center justify-center p-8">
      <div className="text-center">
        <RefreshCw
          size={24}
          className="mx-auto animate-spin text-blue-400"
        />

        <p className="mt-4 text-sm font-medium text-slate-400">
          Loading attendance...
        </p>

        <p className="mt-1 text-xs text-slate-600">
          Fetching records from the classroom
          history service.
        </p>
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex min-h-[280px] items-center justify-center p-8">
      <div className="max-w-md text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-800/70 text-slate-500">
          <ClipboardCheck size={22} />
        </div>

        <h3 className="mt-4 text-sm font-semibold text-slate-300">
          No attendance records
        </h3>

        <p className="mt-2 text-xs leading-5 text-slate-600">
          The selected classroom session does
          not contain attendance records yet.
        </p>
      </div>
    </div>
  )
}

function formatDateTime(
  value,
) {
  if (!value) {
    return '—'
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return '—'
  }

  return date.toLocaleString(
    undefined,
    {
      dateStyle: 'medium',
      timeStyle: 'short',
    },
  )
}

function formatDuration(
  seconds,
) {
  if (
    seconds === null ||
    seconds === undefined
  ) {
    return '—'
  }

  const totalSeconds = Number(seconds)

  if (
    !Number.isFinite(totalSeconds) ||
    totalSeconds < 0
  ) {
    return '—'
  }

  const minutes = Math.floor(
    totalSeconds / 60,
  )

  const remainingSeconds =
    Math.floor(totalSeconds % 60)

  if (minutes === 0) {
    return `${remainingSeconds}s`
  }

  return `${minutes}m ${remainingSeconds}s`
}

function getErrorMessage(
  error,
  fallback,
) {
  return (
    error?.response?.data?.detail ||
    error?.message ||
    fallback
  )
}