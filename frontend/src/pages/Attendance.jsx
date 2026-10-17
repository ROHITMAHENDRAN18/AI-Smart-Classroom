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
  getClassroomAttendance,
  getSessionAttendance,
  getStudents,
  markSessionAttendance,
} from '../services/attendanceService'
import { getMonitoringSummary } from '../services/monitoringService'
import {
  notifyClassroomDataChanged,
  subscribeToClassroomDataChanges,
} from '../utils/classroomDataEvents'

const PAGE_SIZE = 50

export default function Attendance() {
  const [sessions, setSessions] = useState([])
  const [selectedSessionId, setSelectedSessionId] =
    useState('')

  const [records, setRecords] = useState([])
  const [attendanceReport, setAttendanceReport] = useState(null)
  const [unknownDetections, setUnknownDetections] = useState(null)
  const [unknownDetectionsError, setUnknownDetectionsError] = useState(false)
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [offset, setOffset] = useState(0)
  const [refreshKey, setRefreshKey] = useState(0)
  const [students, setStudents] = useState([])
  const [manualStatuses, setManualStatuses] = useState({})
  const [savingManual, setSavingManual] = useState(false)

  const [loadingSessions, setLoadingSessions] =
    useState(true)

  const [loadingAttendance, setLoadingAttendance] =
    useState(false)

  const [error, setError] = useState('')

  const loadSessions = useCallback(
    async (signal) => {
      try {
        setLoadingSessions(true)
        setError('')

        const data = await getAttendanceSessions({ signal })

        if (signal?.aborted) return
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
        if (signal?.aborted) return
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
        if (!signal?.aborted) setLoadingSessions(false)
      }
    },
    [],
  )

  const loadAttendance = useCallback(
    async (sessionId, signal) => {
      if (!sessionId) {
        setRecords([])
        setAttendanceReport(null)
        setUnknownDetections(0)
        setUnknownDetectionsError(false)
        setLoadingAttendance(false)
        return
      }

      try {
        setLoadingAttendance(true)
        setError('')
        setManualStatuses({})
        setRecords([])
        setAttendanceReport(null)
        setUnknownDetections(null)
        setUnknownDetectionsError(false)

        const [attendanceResult, summaryResult] = await Promise.allSettled([
          getClassroomAttendance({
            sessionId,
            date,
            limit: PAGE_SIZE,
            offset,
            signal,
          }),
          getMonitoringSummary({
            classroomId: sessions.find((session) => session.session_id === sessionId)?.classroom_id,
            sessionId,
            signal,
          }),
        ])

        if (signal?.aborted) return
        if (attendanceResult.status === 'rejected') throw attendanceResult.reason
        const data = attendanceResult.value
        setAttendanceReport(data)
        setRecords(data.records.map((record) => ({
          ...record,
          studentId: record.student_name
            ? `${record.student_name} (${record.student_id})`
            : record.student_id,
          recordedAt: record.recorded_at,
        })))
        if (summaryResult.status === 'fulfilled') {
          setUnknownDetections(summaryResult.value.unknown_detections)
        } else if (summaryResult.reason?.response?.status === 404) {
          setUnknownDetections(0)
        } else {
          setUnknownDetections(null)
          setUnknownDetectionsError(true)
          console.error('Failed to load unknown face observations:', summaryResult.reason)
        }
      } catch (requestError) {
        if (signal?.aborted) return
        console.error(
          'Failed to load attendance:',
          requestError,
        )

        setRecords([])
        setAttendanceReport(null)

        setError(
          getErrorMessage(
            requestError,
            'Unable to load attendance records.',
          ),
        )
      } finally {
        if (!signal?.aborted) setLoadingAttendance(false)
      }
    },
    [date, offset, sessions],
  )

  useEffect(() => {
    const controller = new AbortController()
    loadSessions(controller.signal)
    return () => controller.abort()
  }, [loadSessions, refreshKey])

  useEffect(() => {
    const controller = new AbortController()
    loadAttendance(selectedSessionId, controller.signal)
    return () => controller.abort()
  }, [
    selectedSessionId,
    loadAttendance,
    refreshKey,
  ])

  useEffect(
    () =>
      subscribeToClassroomDataChanges(() =>
        setRefreshKey((current) => current + 1),
      ),
    [],
  )

  useEffect(() => {
    const controller = new AbortController()
    getStudents({ signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) setStudents(data)
      })
      .catch((requestError) => {
        if (!controller.signal.aborted) {
          console.error('Failed to load the attendance roster:', requestError)
          setError(
            requestError?.response?.data?.detail ||
              requestError?.message ||
              'Unable to load the classroom roster for manual attendance.',
          )
        }
      })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    setManualStatuses({})
    if (!selectedSessionId) return () => controller.abort()

    getSessionAttendance(selectedSessionId, { signal: controller.signal })
      .then((existingRecords) => {
        if (controller.signal.aborted) return
        setManualStatuses(
          Object.fromEntries(
            existingRecords.map((record) => [
              record.student_id,
              record.status,
            ]),
          ),
        )
      })
      .catch((requestError) => {
        if (!controller.signal.aborted) {
          console.error('Failed to load existing session attendance:', requestError)
          setError(
            requestError?.response?.data?.detail ||
              requestError?.message ||
              'Unable to load existing attendance for this session.',
          )
        }
      })
    return () => controller.abort()
  }, [selectedSessionId, refreshKey])

  const summary = useMemo(() => {
    return {
      present: attendanceReport?.present_count ?? null,
      absent: attendanceReport?.absent_count ?? null,
      unknown: attendanceReport?.unknown_count ?? null,
      unknownDetections,
      total: attendanceReport?.total_records ?? null,
      percentage: attendanceReport?.attendance_rate ?? null,
    }
  }, [attendanceReport, unknownDetections])

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
  const activeStudents = useMemo(
    () =>
      students.filter(
        (student) => student.classroom_is_active === true,
      ),
    [students],
  )
  const hasCompleteManualStatuses = activeStudents.every((student) =>
    ['PRESENT', 'ABSENT', 'UNKNOWN'].includes(
      manualStatuses[student.student_id],
    ),
  )

  async function handleRefresh() {
    setRefreshKey((current) => current + 1)
  }

  async function handleSaveManualAttendance() {
    if (
      savingManual ||
      selectedSession?.status !== 'ACTIVE' ||
      !selectedSessionId
    ) {
      return
    }

    setSavingManual(true)
    setError('')
    try {
      if (!activeStudents.length) {
        setError('No active enrolled students are available to mark.')
        return
      }
      if (!hasCompleteManualStatuses) {
        setError('Choose a status for every active enrolled student.')
        return
      }
      await markSessionAttendance(
        selectedSessionId,
        activeStudents.map((student) => ({
          student_id: student.student_id,
          status: manualStatuses[student.student_id],
        })),
      )
      notifyClassroomDataChanged()
    } catch (requestError) {
      console.error('Failed to save manual attendance:', requestError)
      setError(
        requestError?.response?.data?.detail ||
          requestError?.message ||
          'Unable to save manual attendance.',
      )
    } finally {
      setSavingManual(false)
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

          <div className="w-full lg:w-auto">
            <label
              htmlFor="attendance-date"
              className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-500"
            >
              UTC date
            </label>
            <input
              id="attendance-date"
              type="date"
              value={date}
              onChange={(event) => {
                setDate(event.target.value)
                setOffset(0)
              }}
              className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-200 outline-none focus:border-blue-500/50"
            />
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

      {selectedSession?.status === 'ACTIVE' && (
        <section className="surface mb-6 p-5 sm:p-6">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-base font-semibold text-white">
                Manual attendance
              </h2>
              <p className="mt-1 text-xs text-slate-400">
                YOLO detections do not identify students. Review each enrolled
                student and explicitly choose PRESENT, ABSENT, or UNKNOWN.
              </p>
            </div>
            <button
              type="button"
              onClick={handleSaveManualAttendance}
              disabled={
                savingManual ||
                loadingAttendance ||
                activeStudents.length === 0 ||
                !hasCompleteManualStatuses
              }
              className="rounded-lg border border-blue-400/20 bg-blue-500/10 px-4 py-2 text-sm font-medium text-blue-200 hover:bg-blue-500/20 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {savingManual ? 'Saving…' : 'Save attendance'}
            </button>
          </div>
          {activeStudents.length === 0 ? (
            <p className="text-sm text-slate-500">
              No enrolled students are available to mark.
            </p>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {activeStudents.map((student) => (
                <label
                  key={student.student_id}
                  className="flex items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-950/50 px-3 py-2"
                >
                  <span className="min-w-0 truncate text-sm text-slate-200">
                    {student.name} <span className="text-slate-500">({student.student_id})</span>
                  </span>
                  <select
                    aria-label={`Attendance status for ${student.name}`}
                    value={manualStatuses[student.student_id] || ''}
                    onChange={(event) =>
                      {
                        setError('')
                        setManualStatuses((current) => ({
                          ...current,
                          [student.student_id]: event.target.value,
                        }))
                      }
                    }
                    disabled={savingManual}
                    className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-200"
                  >
                    <option value="">Choose status</option>
                    <option value="PRESENT">Present</option>
                    <option value="ABSENT">Absent</option>
                    <option value="UNKNOWN">Unknown</option>
                  </select>
                </label>
              ))}
            </div>
          )}
        </section>
      )}

      <section className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
        <SummaryCard
          icon={<Users size={19} />}
          label="Total Records"
          value={loadingAttendance ? '…' : summary.total ?? '—'}
          description="Attendance records"
          iconClass="bg-blue-500/10 text-blue-400"
        />

        <SummaryCard
          icon={
            <CheckCircle2 size={19} />
          }
          label="Present"
          value={loadingAttendance ? '…' : summary.present ?? '—'}
          description="Marked present"
          iconClass="bg-emerald-500/10 text-emerald-400"
        />

        <SummaryCard
          icon={<UserX size={19} />}
          label="Absent"
          value={loadingAttendance ? '…' : summary.absent ?? '—'}
          description="Marked absent"
          iconClass="bg-red-500/10 text-red-400"
        />

        <SummaryCard
          icon={<AlertCircle size={19} />}
          label="Unknown Attendance Records"
          value={loadingAttendance ? '…' : summary.unknown ?? '—'}
          description="Persisted records with unknown status"
          iconClass="bg-slate-500/10 text-slate-400"
        />

        <SummaryCard
          icon={<AlertCircle size={19} />}
          label="Unknown Face Observations"
          value={loadingAttendance
            ? '…'
            : unknownDetectionsError
              ? '—'
              : summary.unknownDetections ?? '—'}
          description={unknownDetectionsError
            ? 'Could not load this session’s frame summary'
            : 'Unknown face detections across processed frames'}
          iconClass="bg-amber-500/10 text-amber-400"
        />

        <SummaryCard
          icon={
            <ClipboardCheck size={19} />
          }
          label="Attendance Rate"
          value={loadingAttendance
            ? '…'
            : summary.percentage === null
              ? '—'
              : `${summary.percentage.toFixed(1)}%`}
          description="Present / known present + absent"
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
          <>
            <AttendanceTable records={records} />
            <div className="flex items-center justify-between border-t border-slate-800 px-5 py-4">
              <p className="text-xs text-slate-500">
                {attendanceReport?.total_records ?? 0} records for {attendanceReport?.from_date ?? date} (UTC)
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setOffset((value) => Math.max(0, value - PAGE_SIZE))}
                  disabled={offset === 0 || loadingAttendance}
                  className="rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-300 disabled:opacity-40"
                >
                  Previous
                </button>
                <button
                  type="button"
                  onClick={() => setOffset((value) => value + PAGE_SIZE)}
                  disabled={offset + records.length >= (attendanceReport?.total_records ?? 0) || loadingAttendance}
                  className="rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-300 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          </>
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
              Source
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

                <td className="px-5 py-4 text-xs text-slate-400">
                  {record.attendance_source === 'MANUAL'
                    ? 'Teacher entered'
                    : record.attendance_source === 'AUTOMATIC'
                      ? 'Verified automatic'
                      : 'Not recorded'}
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
