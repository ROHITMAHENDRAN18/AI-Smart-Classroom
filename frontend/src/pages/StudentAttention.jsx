import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  Activity,
  CheckCircle2,
  Eye,
  RefreshCw,
  UserRound,
  Users,
  UserX,
  Wifi,
  WifiOff,
} from 'lucide-react'

import {
  getStudentAttention,
  normalizeStudentAttention,
} from '../services/studentAttentionService'

const POLL_INTERVAL = 1000

export default function StudentAttention() {
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(true)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState('')
  const [lastUpdated, setLastUpdated] = useState(null)

  const loadStudents = useCallback(async () => {
    try {
      const data = await getStudentAttention()

      const normalizedStudents =
        normalizeStudentAttention(data)

      setStudents(normalizedStudents)
      setConnected(true)
      setError('')
      setLastUpdated(new Date())
    } catch (requestError) {
      console.error(
        'Failed to load student attention:',
        requestError,
      )

      setConnected(false)

      setError(
        requestError?.response?.data?.detail ||
          requestError?.message ||
          'Unable to connect to the classroom monitoring server.',
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadStudents()

    const interval = window.setInterval(
      loadStudents,
      POLL_INTERVAL,
    )

    return () => {
      window.clearInterval(interval)
    }
  }, [loadStudents])

  const summary = useMemo(() => {
    const attentive = students.filter(
      (student) =>
        student.attention === 'ATTENTIVE',
    ).length

    const notAttentive = students.filter(
      (student) =>
        student.attention === 'NOT ATTENTIVE',
    ).length

    const unknown = students.filter(
      (student) =>
        student.attention === 'UNKNOWN',
    ).length

    const recognized = students.filter(
      (student) =>
        student.recognized &&
        student.studentId,
    ).length

    return {
      total: students.length,
      recognized,
      attentive,
      notAttentive,
      unknown,
    }
  }, [students])

  return (
    <div className="mx-auto max-w-[1600px] p-4 sm:p-6 lg:p-8">
      <header className="mb-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-medium text-blue-400">
                AI classroom monitoring
              </p>

              <span
                className={`status-pill ${
                  connected
                    ? 'status-pill-success'
                    : 'status-pill-danger'
                }`}
              >
                <span
                  className={`status-dot ${
                    connected
                      ? 'status-dot-success'
                      : 'status-dot-danger'
                  }`}
                />

                {connected
                  ? 'Live'
                  : 'Disconnected'}
              </span>
            </div>

            <h1 className="mt-2 text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Student Attention
            </h1>

            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
              Monitor the current attention state of
              detected students in the classroom.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {lastUpdated && (
              <span className="hidden text-xs text-slate-600 sm:block">
                Updated {formatTime(lastUpdated)}
              </span>
            )}

            <button
              type="button"
              onClick={loadStudents}
              className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/70 px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:border-slate-700 hover:bg-slate-800 hover:text-white"
            >
              <RefreshCw size={16} />
              Refresh
            </button>
          </div>
        </div>
      </header>

      {error && (
        <div className="mb-5 flex items-start gap-3 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3">
          <WifiOff
            size={18}
            className="mt-0.5 shrink-0 text-red-400"
          />

          <div>
            <p className="text-sm font-medium text-red-300">
              Monitoring connection problem
            </p>

            <p className="mt-1 text-xs text-red-300/70">
              {error}
            </p>
          </div>
        </div>
      )}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <SummaryCard
          icon={<Users size={19} />}
          label="Detected"
          value={loading ? '...' : summary.total}
          description="Current tracked persons"
          iconClass="bg-blue-500/10 text-blue-400"
        />

        <SummaryCard
          icon={<UserRound size={19} />}
          label="Recognized"
          value={loading ? '...' : summary.recognized}
          description="Recognized students"
          iconClass="bg-cyan-500/10 text-cyan-400"
        />

        <SummaryCard
          icon={<CheckCircle2 size={19} />}
          label="Attentive"
          value={loading ? '...' : summary.attentive}
          description="Currently attentive"
          iconClass="bg-emerald-500/10 text-emerald-400"
        />

        <SummaryCard
          icon={<UserX size={19} />}
          label="Not Attentive"
          value={
            loading
              ? '...'
              : summary.notAttentive
          }
          description="Attention concerns"
          iconClass="bg-amber-500/10 text-amber-400"
        />

        <SummaryCard
          icon={<Activity size={19} />}
          label="Unknown"
          value={loading ? '...' : summary.unknown}
          description="Awaiting stable state"
          iconClass="bg-slate-500/10 text-slate-400"
        />
      </section>

      <section className="mt-6 surface overflow-hidden">
        <div className="flex flex-col gap-3 border-b border-slate-800 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
          <div>
            <h2 className="text-base font-semibold text-white">
              Live Student Attention
            </h2>

            <p className="mt-1 text-xs text-slate-500">
              Updated automatically every second
            </p>
          </div>

          <div className="flex items-center gap-2">
            {connected ? (
              <Wifi
                size={15}
                className="text-emerald-400"
              />
            ) : (
              <WifiOff
                size={15}
                className="text-red-400"
              />
            )}

            <span
              className={`text-xs font-medium ${
                connected
                  ? 'text-emerald-400'
                  : 'text-red-400'
              }`}
            >
              {connected
                ? 'Monitoring online'
                : 'Monitoring offline'}
            </span>
          </div>
        </div>

        {loading ? (
          <LoadingState />
        ) : students.length === 0 ? (
          <EmptyState connected={connected} />
        ) : (
          <StudentTable students={students} />
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

function StudentTable({ students }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[900px]">
        <thead>
          <tr className="border-b border-slate-800 bg-slate-950/40 text-left">
            <th className="px-5 py-4 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Student
            </th>

            <th className="px-5 py-4 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Track
            </th>

            <th className="px-5 py-4 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Recognition
            </th>

            <th className="px-5 py-4 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Confidence
            </th>

            <th className="px-5 py-4 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Attention
            </th>

            <th className="px-5 py-4 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Head Pose
            </th>
          </tr>
        </thead>

        <tbody>
          {students.map((student, index) => (
            <StudentRow
              key={`${student.trackId}-${student.studentId ?? 'unknown'}-${index}`}
              student={student}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}

function StudentRow({ student }) {
  const confidence = Math.max(
    0,
    Math.min(100, student.similarity * 100),
  )

  return (
    <tr className="border-b border-slate-900 transition hover:bg-slate-900/40">
      <td className="px-5 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
            <UserRound size={17} />
          </div>

          <div>
            <p className="text-sm font-semibold text-white">
              {student.studentId || 'UNKNOWN'}
            </p>

            <p className="mt-0.5 text-[11px] text-slate-600">
              {student.recognized
                ? 'Recognized student'
                : 'Unrecognized person'}
            </p>
          </div>
        </div>
      </td>

      <td className="px-5 py-4">
        <span className="rounded-lg border border-slate-800 bg-slate-950 px-2.5 py-1 text-xs font-medium text-slate-300">
          #{student.trackId}
        </span>
      </td>

      <td className="px-5 py-4">
        <span
          className={`text-xs font-semibold ${
            student.recognized
              ? 'text-emerald-400'
              : 'text-slate-500'
          }`}
        >
          {student.recognized
            ? 'Recognized'
            : 'Unknown'}
        </span>
      </td>

      <td className="px-5 py-4">
        {student.recognized ? (
          <div className="w-32">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400">
                Match
              </span>

              <span className="text-xs font-semibold text-white">
                {confidence.toFixed(1)}%
              </span>
            </div>

            <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800">
              <div
                className="h-full rounded-full bg-blue-400 transition-all duration-500"
                style={{
                  width: `${confidence}%`,
                }}
              />
            </div>
          </div>
        ) : (
          <span className="text-xs text-slate-600">
            —
          </span>
        )}
      </td>

      <td className="px-5 py-4">
        <AttentionBadge
          attention={student.attention}
        />
      </td>

      <td className="px-5 py-4">
        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span>
            Yaw:{' '}
            {formatPose(student.yawRatio)}
          </span>

          <span className="text-slate-700">
            |
          </span>

          <span>
            Pitch:{' '}
            {formatPose(student.pitchRatio)}
          </span>
        </div>
      </td>
    </tr>
  )
}

function AttentionBadge({ attention }) {
  if (attention === 'ATTENTIVE') {
    return (
      <span className="attention-badge attention-attentive">
        <CheckCircle2 size={13} />
        ATTENTIVE
      </span>
    )
  }

  if (attention === 'NOT ATTENTIVE') {
    return (
      <span className="attention-badge attention-not-attentive">
        <Eye size={13} />
        NOT ATTENTIVE
      </span>
    )
  }

  return (
    <span className="attention-badge attention-unknown">
      <Activity size={13} />
      UNKNOWN
    </span>
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
          Loading student attention...
        </p>

        <p className="mt-1 text-xs text-slate-600">
          Connecting to the classroom monitoring server.
        </p>
      </div>
    </div>
  )
}

function EmptyState({ connected }) {
  return (
    <div className="flex min-h-[280px] items-center justify-center p-8">
      <div className="max-w-md text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-800/70 text-slate-500">
          <Users size={22} />
        </div>

        <h3 className="mt-4 text-sm font-semibold text-slate-300">
          {connected
            ? 'No students currently detected'
            : 'Monitoring server unavailable'}
        </h3>

        <p className="mt-2 text-xs leading-5 text-slate-600">
          {connected
            ? 'The AI pipeline has not reported any tracked students yet.'
            : 'Start the classroom monitoring server and refresh this page.'}
        </p>
      </div>
    </div>
  )
}

function formatPose(value) {
  if (value === null || value === undefined) {
    return '—'
  }

  return Number(value).toFixed(2)
}

function formatTime(date) {
  return date.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}