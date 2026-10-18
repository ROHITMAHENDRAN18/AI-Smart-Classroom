import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Activity,
  AlertCircle,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ClipboardCheck,
  Clock,
  FileText,
  RefreshCw,
  User,
  Users,
} from 'lucide-react'
import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'

import {
  getHistorySessions,
  getSessionAttendance,
  getSessionAttention,
  getSessionSummary,
  getStudents,
} from '../services/reports'
import {
  formatConfidence,
  formatDateTime,
  formatDuration,
} from '../utils/formatters'
import { subscribeToClassroomDataChanges } from '../utils/classroomDataEvents'

const ATTENTION_COLORS = {
  attentive: '#10b981', // emerald-500
  partial: '#f59e0b',
  notAttentive: '#f43f5e', // rose-500
  unknown: '#64748b', // slate-500
  listening: '#38bdf8',
  sleeping: '#a78bfa',
  talking: '#fbbf24',
  lookingAway: '#fb7185',
}

function getStatusBadge(status) {
  const norm = String(status || '').toUpperCase()

  if (norm === 'ACTIVE') {
    return {
      label: 'ACTIVE',
      dotClass: 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]',
      pillClass: 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400',
    }
  }

  if (norm === 'COMPLETED') {
    return {
      label: 'COMPLETED',
      dotClass: 'bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,0.5)]',
      pillClass: 'border-blue-500/20 bg-blue-500/10 text-blue-400',
    }
  }

  if (norm === 'INTERRUPTED') {
    return {
      label: 'INTERRUPTED',
      dotClass: 'bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.5)]',
      pillClass: 'border-amber-500/20 bg-amber-500/10 text-amber-400',
    }
  }

  return {
    label: norm || 'UNKNOWN',
    dotClass: 'bg-slate-400',
    pillClass: 'border-slate-700 bg-slate-800/50 text-slate-400',
  }
}

function ChartTooltip({ active, payload }) {
  if (active && payload && payload.length) {
    const item = payload[0].payload
    return (
      <div className="rounded-xl border border-slate-800 bg-[#0c1322]/95 px-3.5 py-2.5 shadow-2xl backdrop-blur-md">
        <div className="flex items-center gap-2 mb-1.5">
          <span
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: item.color }}
          />
          <span className="text-xs font-semibold text-white">
            {item.name}
          </span>
        </div>
        <div className="space-y-0.5 text-[11px] text-slate-400">
          <p>
            Count:{' '}
            <span className="font-mono font-medium text-slate-200">
              {item.value}
            </span>
          </p>
          <p>
            Share:{' '}
            <span className="font-mono font-medium text-slate-200">
              {item.percentage}%
            </span>
          </p>
        </div>
      </div>
    )
  }

  return null
}

export default function Reports() {
  const [students, setStudents] = useState([])
  const [sessions, setSessions] = useState([])
  const [selectedStudentId, setSelectedStudentId] = useState('ALL')
  const [selectedSessionId, setSelectedSessionId] = useState('')
  const [attendanceRecords, setAttendanceRecords] = useState([])
  const [attentionRecords, setAttentionRecords] = useState([])
  const [sessionSummary, setSessionSummary] = useState(null)
  const [reportGeneratedAt, setReportGeneratedAt] = useState(null)
  const [activeTab, setActiveTab] = useState('attendance') // 'attendance' | 'attention'
  const [loadingInitial, setLoadingInitial] = useState(true)
  const [loadingData, setLoadingData] = useState(false)
  const [error, setError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  const loadInitialData = useCallback(async (signal) => {
    setLoadingInitial(true)
    setError('')

    try {
      const [loadedStudents, loadedSessions] = await Promise.all([
        getStudents({ signal }),
        getHistorySessions(50, 0, { signal }),
      ])

      if (signal?.aborted) return
      setStudents(loadedStudents)
      setSessions(loadedSessions)

      setSelectedSessionId((current) => {
        const existingSession = loadedSessions.find(
          (session) => session.session_id === current,
        )

        return existingSession
          ? existingSession.session_id
          : loadedSessions[0]?.session_id ?? ''
      })
    } catch (err) {
      if (signal?.aborted) return
      console.error('Failed to load Reports data:', err)

      setStudents([])
      setSessions([])
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          'Unable to load Reports data. Check the backend and try again.',
      )
    } finally {
      if (!signal?.aborted) setLoadingInitial(false)
    }
  }, [])

  // Load session summary, attendance, attention, and analytics for selected session/student
  const loadReportDetails = useCallback(async (sessionId, signal) => {
    if (!sessionId) {
      setSessionSummary(null)
      setAttendanceRecords([])
      setAttentionRecords([])
      setReportGeneratedAt(null)
      setLoadingData(false)
      return
    }

    setSessionSummary(null)
    setAttendanceRecords([])
    setAttentionRecords([])
    setReportGeneratedAt(null)
    try {
      setLoadingData(true)
      setError('')

      const [summaryData, attendanceData, attentionData] =
        await Promise.all([
          getSessionSummary(sessionId, { signal }),
          getSessionAttendance(sessionId, { signal }),
          getSessionAttention(sessionId, { signal }),
        ])

      if (signal?.aborted) return
      setSessionSummary(summaryData)
      setAttendanceRecords(attendanceData)
      setAttentionRecords(attentionData)
      setReportGeneratedAt(new Date().toISOString())
    } catch (err) {
      if (signal?.aborted) return
      console.error(`Failed to load report details for ${sessionId}:`, err)

      setSessionSummary(null)
      setAttendanceRecords([])
      setAttentionRecords([])
      setReportGeneratedAt(null)

      if (err.response?.status === 401) {
        setError('Your session has expired. Please log in again.')
      } else if (err.response?.status === 404) {
        setError('No report data is available for this session.')
      } else {
        setError('Unable to load report records. Please try again.')
      }
    } finally {
      if (!signal?.aborted) setLoadingData(false)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    loadInitialData(controller.signal)
    return () => controller.abort()
  }, [loadInitialData, refreshKey])

  useEffect(() => {
    const controller = new AbortController()
    loadReportDetails(selectedSessionId, controller.signal)
    return () => controller.abort()
  }, [selectedSessionId, loadReportDetails, refreshKey])

  useEffect(
    () =>
      subscribeToClassroomDataChanges(() =>
        setRefreshKey((current) => current + 1),
      ),
    [],
  )

  const handleRefresh = () => setRefreshKey((current) => current + 1)

  // Selected student object
  const selectedStudent = useMemo(() => {
    if (selectedStudentId === 'ALL') {
      return null
    }
    return students.find((s) => s.student_id === selectedStudentId) || null
  }, [students, selectedStudentId])

  // Selected session object
  const selectedSession = useMemo(() => {
    return sessions.find((s) => s.session_id === selectedSessionId) || null
  }, [sessions, selectedSessionId])

  // Filter records by selected student
  const filteredAttendance = useMemo(() => {
    if (selectedStudentId === 'ALL') {
      return attendanceRecords
    }
    return attendanceRecords.filter((r) => r.student_id === selectedStudentId)
  }, [attendanceRecords, selectedStudentId])

  const filteredAttention = useMemo(() => {
    if (selectedStudentId === 'ALL') {
      return attentionRecords
    }
    return attentionRecords.filter((r) => r.student_id === selectedStudentId)
  }, [attentionRecords, selectedStudentId])

  // Attendance metrics
  const attendanceStats = useMemo(() => {
    const total = filteredAttendance.length
    const presentCount = filteredAttendance.filter(
      (r) => r.status === 'PRESENT',
    ).length
    const absentCount = filteredAttendance.filter(
      (r) => r.status === 'ABSENT',
    ).length

    const knownRecords = presentCount + absentCount
    const attendancePct = knownRecords > 0
      ? Number(((presentCount / knownRecords) * 100).toFixed(1))
      : null

    return {
      total,
      presentCount,
      absentCount,
      attendancePercentage: attendancePct,
    }
  }, [filteredAttendance])

  // Attention metrics
  const attentionStats = useMemo(() => {
    const total = filteredAttention.length
    const behaviorStates = [
      'LISTENING',
      'SLEEPING',
      'POSSIBLY_TALKING',
      'LOOKING_AWAY',
    ]
    const behaviorCounts = Object.fromEntries(
      behaviorStates.map((state) => [
        state,
        filteredAttention.filter((record) => record.attention_state === state).length,
      ]),
    )
    const legacyTotal = filteredAttention.filter((record) =>
      ['ATTENTIVE', 'PARTIAL', 'NOT ATTENTIVE', 'UNKNOWN'].includes(
        record.attention_state,
      ),
    ).length
    const attentiveCount = filteredAttention.filter(
      (r) => r.attention_state === 'ATTENTIVE',
    ).length
    const partialCount = filteredAttention.filter(
      (r) => r.attention_state === 'PARTIAL',
    ).length
    const notAttentiveCount = filteredAttention.filter(
      (r) => r.attention_state === 'NOT ATTENTIVE',
    ).length
    const unknownCount = filteredAttention.filter(
      (r) => r.attention_state === 'UNKNOWN',
    ).length

    const attentivePct = legacyTotal > 0 ? Number(((attentiveCount / legacyTotal) * 100).toFixed(1)) : 0
    const partialPct = legacyTotal > 0 ? Number(((partialCount / legacyTotal) * 100).toFixed(1)) : 0
    const notAttentivePct =
      legacyTotal > 0 ? Number(((notAttentiveCount / legacyTotal) * 100).toFixed(1)) : 0
    const unknownPct = legacyTotal > 0 ? Number(((unknownCount / legacyTotal) * 100).toFixed(1)) : 0

    return {
      total,
      legacyTotal,
      behaviorCounts,
      attentiveCount,
      partialCount,
      notAttentiveCount,
      unknownCount,
      attentivePct,
      partialPct,
      notAttentivePct,
      unknownPct,
    }
  }, [filteredAttention])

  // Donut chart data
  const chartData = useMemo(() => {
    if (attentionStats.total === 0) {
      return []
    }

    return [
      {
        name: 'Legacy attentive score',
        value: attentionStats.attentiveCount,
        percentage: attentionStats.total > 0
          ? Number(((attentionStats.attentiveCount / attentionStats.total) * 100).toFixed(1))
          : 0,
        color: ATTENTION_COLORS.attentive,
      },
      {
        name: 'Legacy partial score',
        value: attentionStats.partialCount,
        percentage: attentionStats.total > 0
          ? Number(((attentionStats.partialCount / attentionStats.total) * 100).toFixed(1))
          : 0,
        color: ATTENTION_COLORS.partial,
      },
      {
        name: 'Legacy not attentive score',
        value: attentionStats.notAttentiveCount,
        percentage: attentionStats.total > 0
          ? Number(((attentionStats.notAttentiveCount / attentionStats.total) * 100).toFixed(1))
          : 0,
        color: ATTENTION_COLORS.notAttentive,
      },
      {
        name: 'Unknown',
        value: attentionStats.unknownCount,
        percentage: attentionStats.total > 0
          ? Number(((attentionStats.unknownCount / attentionStats.total) * 100).toFixed(1))
          : 0,
        color: ATTENTION_COLORS.unknown,
      },
      {
        name: 'Listening posture',
        value: attentionStats.behaviorCounts.LISTENING,
        percentage: attentionStats.total > 0
          ? Number(((attentionStats.behaviorCounts.LISTENING / attentionStats.total) * 100).toFixed(1))
          : 0,
        color: ATTENTION_COLORS.listening,
      },
      {
        name: 'Head down / eyes closed',
        value: attentionStats.behaviorCounts.SLEEPING,
        percentage: attentionStats.total > 0
          ? Number(((attentionStats.behaviorCounts.SLEEPING / attentionStats.total) * 100).toFixed(1))
          : 0,
        color: ATTENTION_COLORS.sleeping,
      },
      {
        name: 'Possibly talking',
        value: attentionStats.behaviorCounts.POSSIBLY_TALKING,
        percentage: attentionStats.total > 0
          ? Number(((attentionStats.behaviorCounts.POSSIBLY_TALKING / attentionStats.total) * 100).toFixed(1))
          : 0,
        color: ATTENTION_COLORS.talking,
      },
      {
        name: 'Looking away',
        value: attentionStats.behaviorCounts.LOOKING_AWAY,
        percentage: attentionStats.total > 0
          ? Number(((attentionStats.behaviorCounts.LOOKING_AWAY / attentionStats.total) * 100).toFixed(1))
          : 0,
        color: ATTENTION_COLORS.lookingAway,
      },
    ]
  }, [attentionStats])

  const sessionStatusBadge = useMemo(() => {
    return getStatusBadge(selectedSession?.status)
  }, [selectedSession])

  const noSessionsAvailable = !loadingInitial && sessions.length === 0
  const noStudentsAvailable = !loadingInitial && students.length === 0

  return (
    <div className="mx-auto max-w-[1600px] p-4 sm:p-6 lg:p-8 space-y-6">
      {/* 1. Header */}
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-blue-400">
            <FileText size={15} />
            Classroom Reports
          </div>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-white sm:text-3xl">
            Reports
          </h1>
          <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-slate-400">
              Review persisted attendance and observable behavior records by
            classroom session. Browser YOLO detections are ephemeral, do not
            identify students, and are not report records. File export is not
            implemented.
          </p>
        </div>

        {/* 2. Filters & Controls */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Student Selector */}
          <div className="relative">
            <select
              aria-label="Filter by student"
              value={selectedStudentId}
              onChange={(e) => setSelectedStudentId(e.target.value)}
              disabled={loadingInitial || loadingData || students.length === 0}
              className="appearance-none rounded-xl border border-slate-800 bg-[#0d1424] py-2.5 pl-3.5 pr-9 text-xs font-medium text-slate-200 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
            >
              <option value="ALL">All Students ({students.length})</option>
              {students.map((st) => (
                <option key={st.student_id} value={st.student_id}>
                  {st.name} ({st.student_id})
                </option>
              ))}
            </select>
            <ChevronDown
              size={14}
              className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"
            />
          </div>

          {/* Session Selector */}
          <div className="relative">
            <select
              aria-label="Filter by session"
              value={selectedSessionId}
              onChange={(e) => setSelectedSessionId(e.target.value)}
              disabled={loadingInitial || loadingData || sessions.length === 0}
              className="appearance-none rounded-xl border border-slate-800 bg-[#0d1424] py-2.5 pl-3.5 pr-9 text-xs font-medium text-slate-200 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
            >
              {sessions.length === 0 && <option value="">No sessions available</option>}
              {sessions.map((sess) => (
                <option key={sess.session_id} value={sess.session_id}>
                  {sess.session_id} ({sess.status})
                </option>
              ))}
            </select>
            <ChevronDown
              size={14}
              className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"
            />
          </div>

          {/* Refresh Button */}
          <button
            type="button"
            onClick={handleRefresh}
            disabled={loadingInitial || loadingData}
            className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2.5 text-xs font-medium text-slate-300 transition hover:border-slate-700 hover:bg-slate-800 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCw
              size={14}
              className={loadingInitial || loadingData ? 'animate-spin' : ''}
            />
            <span>Refresh</span>
          </button>
        </div>
      </header>

      {/* 14. Error State */}
      {error && (
        <div className="flex flex-col gap-3 rounded-2xl border border-red-500/20 bg-red-500/5 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3 text-sm text-red-300">
            <AlertCircle size={18} className="shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
          <button
            type="button"
            onClick={handleRefresh}
            className="flex w-fit items-center gap-2 rounded-lg border border-red-500/20 px-3 py-1.5 text-xs font-medium text-red-300 transition hover:bg-red-500/10"
          >
            <RefreshCw size={13} />
            Retry
          </button>
        </div>
      )}

      {/* 15. Empty State: No sessions or students */}
      {noSessionsAvailable && !error && (
        <div className="surface flex min-h-[340px] flex-col items-center justify-center p-8 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-800 bg-slate-900 text-blue-400">
            <Calendar size={28} />
          </div>
          <h2 className="mt-4 text-lg font-bold text-white">No sessions available.</h2>
          <p className="mt-1.5 max-w-md text-sm text-slate-400">
            Start a classroom session to begin recording attendance and attention reports.
          </p>
        </div>
      )}

      {noStudentsAvailable && !noSessionsAvailable && !error && (
        <div className="surface flex min-h-[340px] flex-col items-center justify-center p-8 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-800 bg-slate-900 text-blue-400">
            <Users size={28} />
          </div>
          <h2 className="mt-4 text-lg font-bold text-white">No students available.</h2>
          <p className="mt-1.5 max-w-md text-sm text-slate-400">
            Register students in the classroom to generate individual reports.
          </p>
        </div>
      )}

      {/* Main Content when sessions/students exist */}
      {!noSessionsAvailable && (
        <>
          {/* Top Row: 3. Student Summary + 7. Session Report */}
          <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Student Summary Panel (7 cols on lg) */}
            <div className="surface p-5 sm:p-6 lg:col-span-7 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <User size={18} className="text-blue-400" />
                    <h2 className="text-base font-semibold text-white">Student Summary</h2>
                  </div>

                  {selectedStudent && (
                    <span className="rounded-lg border border-slate-700 px-3 py-1 text-xs text-slate-500">
                      Export unavailable
                    </span>
                  )}
                </div>

                <p className="mt-1 text-xs text-slate-400">
                  {selectedStudent
                    ? 'Individual student profile and biometric enrollment status.'
                    : 'Showing aggregated report for all enrolled classroom students.'}
                </p>

                {/* Details Grid */}
                {selectedStudent ? (
                  <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                    <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                      <span className="text-[11px] font-medium text-slate-500">Student Name</span>
                      <p className="mt-1 font-semibold text-white truncate">
                        {selectedStudent.name}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                      <span className="text-[11px] font-medium text-slate-500">Student ID</span>
                      <p className="mt-1 font-mono font-semibold text-blue-300">
                        {selectedStudent.student_id}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                      <span className="text-[11px] font-medium text-slate-500">Department</span>
                      <p className="mt-1 font-medium text-slate-300 truncate">
                        {selectedStudent.department}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                      <span className="text-[11px] font-medium text-slate-500">Year & Section</span>
                      <p className="mt-1 font-medium text-slate-300">
                        Year {selectedStudent.year} • Section {selectedStudent.section}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                      <span className="text-[11px] font-medium text-slate-500">Email</span>
                      <p className="mt-1 font-medium text-slate-300 truncate">
                        {selectedStudent.email || '—'}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3 flex flex-col justify-between">
                      <span className="text-[11px] font-medium text-slate-500">Face Registered</span>
                      <div className="mt-1 flex items-center gap-1.5">
                        {selectedStudent.face_registered ? (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-400">
                            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                            Registered
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-400">
                            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                            Not Registered
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="mt-5 rounded-xl border border-slate-800 bg-slate-950/40 p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-xs font-semibold text-white">All Classroom Students</p>
                        <p className="mt-1 text-xs text-slate-400">
                          {students.length} student{students.length === 1 ? '' : 's'} currently registered.
                        </p>
                      </div>
                      <span className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 font-mono text-xs font-bold text-blue-400">
                        {students.length} Total
                      </span>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {students.map((st) => (
                        <button
                          key={st.student_id}
                          type="button"
                          onClick={() => setSelectedStudentId(st.student_id)}
                          className="rounded-lg border border-slate-800 bg-slate-900/60 px-2 py-1 text-[11px] font-mono text-slate-300 transition hover:border-blue-500/40 hover:text-blue-300"
                        >
                          {st.student_id} ({st.name})
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* 7. Session Report Panel (5 cols on lg) */}
            <div className="surface p-5 sm:p-6 lg:col-span-5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Clock size={18} className="text-blue-400" />
                    <h2 className="text-base font-semibold text-white">Session Details</h2>
                  </div>
                  {selectedSession && (
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${sessionStatusBadge.pillClass}`}
                    >
                      <span className={`h-1.5 w-1.5 rounded-full ${sessionStatusBadge.dotClass}`} />
                      {sessionStatusBadge.label}
                    </span>
                  )}
                </div>

                <p className="mt-1 text-xs text-slate-400">
                  Timeline and status for the active session filter.
                </p>

                <div className="mt-5 space-y-3 text-xs">
                  <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                    <span className="text-[11px] font-medium text-slate-500">Session ID</span>
                    <p className="mt-1 font-mono font-semibold text-blue-300 break-all">
                      {selectedSession?.session_id || '—'}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                      <div className="flex items-center gap-1 text-[11px] text-slate-500">
                        <Calendar size={12} />
                        <span>Started</span>
                      </div>
                      <p className="mt-1 font-medium text-slate-200 truncate">
                        {formatDateTime(selectedSession?.started_at)}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                      <div className="flex items-center gap-1 text-[11px] text-slate-500">
                        <Clock size={12} />
                        <span>Duration</span>
                      </div>
                      <p className="mt-1 font-mono font-medium text-slate-200">
                        {formatDuration(
                          sessionSummary?.session?.duration_seconds ??
                          selectedSession?.duration_seconds,
                        )}
                      </p>
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                    <div className="flex items-center gap-1 text-[11px] text-slate-500">
                      <Calendar size={12} />
                      <span>Ended</span>
                    </div>
                    <p className="mt-1 font-medium text-slate-300 truncate">
                      {selectedSession?.ended_at
                        ? formatDateTime(selectedSession.ended_at)
                        : selectedSession?.status === 'ACTIVE'
                          ? 'Session in progress'
                          : '—'}
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                      <span className="text-[11px] text-slate-500">Reporting period</span>
                      <p className="mt-1 text-xs font-medium text-slate-300">
                        {selectedSession?.started_at
                          ? `${formatDateTime(selectedSession.started_at)} – ${
                            selectedSession.ended_at
                              ? formatDateTime(selectedSession.ended_at)
                              : 'In progress'
                          }`
                          : '—'}
                      </p>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                      <span className="text-[11px] text-slate-500">Data fetched</span>
                      <p className="mt-1 text-xs font-medium text-slate-300">
                        {formatDateTime(reportGeneratedAt)}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* 4 & 5. Summary Cards Grid (Desktop: 2-4 per row, Tablet: 2, Mobile: 1) */}
          <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Attendance Records */}
            <ReportMetricCard
              icon={<ClipboardCheck size={18} />}
              label="Attendance Records"
              value={loadingData ? null : error ? '—' : attendanceStats.total}
              description={error ? 'Report data unavailable' : `Present: ${attendanceStats.presentCount} | Absent: ${attendanceStats.absentCount}`}
              iconClass="bg-indigo-500/10 text-indigo-400"
            />

            {/* Attendance Percentage */}
            <ReportMetricCard
              icon={<CheckCircle2 size={18} />}
              label="Attendance Rate"
              value={
                loadingData
                  ? null
                  : error
                    ? '—'
                  : attendanceStats.attendancePercentage !== null
                    ? `${attendanceStats.attendancePercentage}%`
                    : '—'
              }
              description={
                error
                  ? 'Report data unavailable'
                  : attendanceStats.total > 0
                  ? `${attendanceStats.presentCount} verified check-ins`
                  : 'No attendance records logged'
              }
              iconClass="bg-blue-500/10 text-blue-400"
            />

            {/* Attention Records */}
            <ReportMetricCard
              icon={<Activity size={18} />}
              label="Behavior Observations"
              value={loadingData ? null : error ? '—' : attentionStats.total}
              description={error ? 'Report data unavailable' : 'Visible posture estimates; not a measure of mental attention'}
              iconClass="bg-purple-500/10 text-purple-400"
            />

            {/* Attentive Percentage */}
            <ReportMetricCard
              icon={<CheckCircle2 size={18} />}
              label="Legacy Attentive Rate"
              value={
                loadingData
                  ? null
                  : error
                    ? '—'
                  : attentionStats.legacyTotal > 0
                    ? `${attentionStats.attentivePct}%`
                    : '—'
              }
              description={error
                ? 'Report data unavailable'
                : 'Based only on older attention-score records; new behavior labels are reported separately.'}
              iconClass="bg-emerald-500/10 text-emerald-400"
            />
          </section>

          {/* 6. Attention Distribution Chart + Breakdown */}
          <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="surface p-5 sm:p-6 lg:col-span-7 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-base font-semibold text-white">
                      Attention Distribution
                    </h2>
                    <p className="mt-1 text-xs text-slate-400">
                      Breakdown of attentiveness states for the current filter.
                    </p>
                  </div>
                  <span className="rounded-lg border border-slate-800 bg-slate-900/60 px-2.5 py-1 text-[11px] font-medium text-slate-400">
                    Distribution
                  </span>
                </div>

                <div className="mt-6 flex flex-col items-center justify-center min-h-[250px]">
                  {loadingData ? (
                    <div className="flex h-[250px] w-full flex-col items-center justify-center gap-3">
                      <div className="h-36 w-36 rounded-full border-4 border-slate-800 border-t-blue-500 animate-spin" />
                      <p className="text-xs text-slate-500">Loading chart data...</p>
                    </div>
                  ) : error ? (
                    <p className="text-sm text-red-300">Attention records could not be loaded.</p>
                  ) : chartData.length > 0 ? (
                    <div className="w-full">
                      <div className="relative h-[220px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={chartData}
                              cx="50%"
                              cy="50%"
                              innerRadius={60}
                              outerRadius={88}
                              paddingAngle={4}
                              dataKey="value"
                              stroke="none"
                            >
                              {chartData.map((entry) => (
                                <Cell key={entry.name} fill={entry.color} />
                              ))}
                            </Pie>
                            <Tooltip content={<ChartTooltip />} />
                          </PieChart>
                        </ResponsiveContainer>
                        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
                          <span className="text-2xl font-bold tracking-tight text-white">
                            {attentionStats.attentivePct}%
                          </span>
                          <span className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                            Attentive
                          </span>
                        </div>
                      </div>

                      <div className="mt-4 grid grid-cols-3 gap-2 border-t border-slate-800/80 pt-4">
                        {chartData.map((item) => (
                          <div
                            key={item.name}
                            className="flex flex-col items-center rounded-xl border border-slate-800/50 bg-slate-950/40 p-2 text-center"
                          >
                            <div className="flex items-center gap-1.5 text-xs text-slate-400">
                              <span
                                className="h-2 w-2 rounded-full"
                                style={{ backgroundColor: item.color }}
                              />
                              <span className="truncate">{item.name}</span>
                            </div>
                            <span className="mt-1 text-sm font-bold text-white">
                              {item.percentage}%
                            </span>
                            <span className="text-[10px] text-slate-500">
                              {item.value} records
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="flex h-[240px] flex-col items-center justify-center text-center p-4">
                      <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-slate-800 bg-slate-900 text-slate-600 mb-2">
                        <Activity size={22} />
                      </div>
                      <p className="text-sm font-medium text-slate-300">
                        No attention data available.
                      </p>
                      <p className="mt-1 max-w-xs text-xs text-slate-500">
                        No attention detections recorded for this student/session selection.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Attendance & Attention Statistics Summary (5 cols on lg) */}
            <div className="surface p-5 sm:p-6 lg:col-span-5 flex flex-col justify-between">
              <div>
                <h2 className="text-base font-semibold text-white">Report Insights</h2>
                <p className="mt-1 text-xs text-slate-400">
              Attendance records and estimated visible behavior states.
                </p>

                <div className="mt-5 space-y-3 text-xs">
                  <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Present Check-ins</span>
                      <span className="font-mono font-bold text-emerald-400">
                        {attendanceStats.presentCount}
                      </span>
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Absent Records</span>
                      <span className="font-mono font-bold text-rose-400">
                        {attendanceStats.absentCount}
                      </span>
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Legacy Attentive Scores</span>
                      <span className="font-mono font-bold text-emerald-400">
                        {attentionStats.attentiveCount} ({attentionStats.attentivePct}%)
                      </span>
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Legacy Partial Scores</span>
                      <span className="font-mono font-bold text-rose-400">
                        {attentionStats.partialCount} ({attentionStats.partialPct}%)
                      </span>
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Legacy Not Attentive Scores</span>
                      <span className="font-mono font-bold text-rose-400">
                        {attentionStats.notAttentiveCount} ({attentionStats.notAttentivePct}%)
                      </span>
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Unclassified / Unknown</span>
                      <span className="font-mono font-bold text-slate-400">
                        {attentionStats.unknownCount} ({attentionStats.unknownPct}%)
                      </span>
                    </div>
                  </div>

                  {Object.entries(attentionStats.behaviorCounts).map(([state, count]) => (
                    <div key={state} className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">{state.replaceAll('_', ' ')}</span>
                        <span className="font-mono font-bold text-slate-200">{count}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* 8. Report Records Table */}
          <section className="surface p-5 sm:p-6 space-y-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-4">
              <div>
                <h2 className="text-base font-semibold text-white">Report Records</h2>
                <p className="text-xs text-slate-400">
                  Granular timestamped records for the current filter.
                </p>
              </div>

              {/* Table Tab Buttons */}
              <div className="flex items-center gap-1 rounded-xl border border-slate-800 bg-slate-950 p-1">
                <button
                  type="button"
                  onClick={() => setActiveTab('attendance')}
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                    activeTab === 'attendance'
                      ? 'bg-blue-500/20 text-blue-300 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <ClipboardCheck size={14} />
                  <span>Attendance ({filteredAttendance.length})</span>
                </button>

                <button
                  type="button"
                  onClick={() => setActiveTab('attention')}
                  className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                    activeTab === 'attention'
                      ? 'bg-blue-500/20 text-blue-300 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Activity size={14} />
                  <span>Behavior ({filteredAttention.length})</span>
                </button>
              </div>
            </div>

            {/* Attendance Table */}
            {activeTab === 'attendance' && (
              <div className="overflow-x-auto">
                {filteredAttendance.length > 0 ? (
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-500">
                        <th className="py-3 px-3">Date / Time</th>
                        <th className="py-3 px-3">Student ID</th>
                        <th className="py-3 px-3">Status</th>
                        <th className="py-3 px-3">Confidence</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {filteredAttendance.map((rec, idx) => (
                        <tr
                          key={rec.id || `att-${idx}`}
                          className="hover:bg-slate-900/60 transition-colors"
                        >
                          <td className="py-3 px-3 text-slate-300 whitespace-nowrap">
                            {formatDateTime(rec.recorded_at)}
                          </td>
                          <td className="py-3 px-3 font-mono font-medium text-blue-300 whitespace-nowrap">
                            {rec.student_id}
                          </td>
                          <td className="py-3 px-3">
                            <span
                              className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                                rec.status === 'PRESENT'
                                  ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400'
                                  : rec.status === 'ABSENT'
                                    ? 'border-rose-500/20 bg-rose-500/10 text-rose-400'
                                    : 'border-slate-700 bg-slate-800 text-slate-400'
                              }`}
                            >
                              {rec.status}
                            </span>
                          </td>
                          <td className="py-3 px-3 font-mono text-slate-300">
                            {formatConfidence(rec.confidence)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="flex min-h-[160px] flex-col items-center justify-center p-6 text-center">
                    <p className="text-sm font-medium text-slate-400">
                      No report data available for this selection.
                    </p>
                    <p className="mt-1 text-xs text-slate-600">
                      No attendance entries logged for the selected student and session.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Attention Table */}
            {activeTab === 'attention' && (
              <div className="overflow-x-auto">
                {filteredAttention.length > 0 ? (
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-500">
                        <th className="py-3 px-3">Date / Time</th>
                        <th className="py-3 px-3">Student ID</th>
                        <th className="py-3 px-3">Track ID</th>
                        <th className="py-3 px-3">Behavior State</th>
                        <th className="py-3 px-3">Confidence</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {filteredAttention.map((rec, idx) => (
                        <tr
                          key={rec.id || `attn-${idx}`}
                          className="hover:bg-slate-900/60 transition-colors"
                        >
                          <td className="py-3 px-3 text-slate-300 whitespace-nowrap">
                            {formatDateTime(rec.recorded_at)}
                          </td>
                          <td className="py-3 px-3 font-mono font-medium text-blue-300 whitespace-nowrap">
                            {rec.student_id}
                          </td>
                          <td className="py-3 px-3 font-mono text-slate-400">
                            {rec.track_id !== null ? `#${rec.track_id}` : '—'}
                          </td>
                          <td className="py-3 px-3">
                            <span
                              className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                                rec.attention_state === 'ATTENTIVE'
                                  ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400'
                                  : rec.attention_state === 'NOT ATTENTIVE'
                                    ? 'border-rose-500/20 bg-rose-500/10 text-rose-400'
                                    : 'border-slate-700 bg-slate-800 text-slate-400'
                              }`}
                            >
                              {rec.attention_state}
                            </span>
                          </td>
                          <td className="py-3 px-3 font-mono text-slate-300">
                            {formatConfidence(rec.confidence)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="flex min-h-[160px] flex-col items-center justify-center p-6 text-center">
                    <p className="text-sm font-medium text-slate-400">
                      No report data available for this selection.
                    </p>
                    <p className="mt-1 text-xs text-slate-600">
                      No attention entries logged for the selected student and session.
                    </p>
                  </div>
                )}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}

function ReportMetricCard({
  icon,
  label,
  value,
  description,
  iconClass,
}) {
  return (
    <div className="surface p-5 transition duration-200 hover:border-slate-700 flex flex-col justify-between">
      <div className="flex items-start justify-between gap-4">
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-xl ${iconClass}`}
        >
          {icon}
        </div>
        <span className="rounded-full border border-slate-800 bg-slate-900/60 px-2 py-0.5 text-[10px] font-medium text-slate-400">
          Report
        </span>
      </div>

      <div className="mt-4">
        <p className="text-xs font-medium uppercase tracking-wider text-slate-400">
          {label}
        </p>
        <div className="mt-1 min-h-[32px] flex items-center">
          {value === null ? (
            <div className="h-7 w-20 rounded-md bg-slate-800/80 animate-pulse" />
          ) : (
            <p className="truncate text-2xl font-bold tracking-tight text-white">
              {value}
            </p>
          )}
        </div>
        <p className="mt-1 truncate text-xs text-slate-500">
          {description}
        </p>
      </div>
    </div>
  )
}
