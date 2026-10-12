import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  BarChart3,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ClipboardCheck,
  Clock,
  HelpCircle,
  RefreshCw,
  Users,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import {
  getClassroomAttendance,
  getHistorySessions,
  getSessionSummary,
} from '../services/analytics'
import {
  formatDateTime,
  formatDuration,
} from '../utils/formatters'

const ATTENTION_COLORS = {
  attentive: '#10b981', // emerald-500
  notAttentive: '#f43f5e', // rose-500
  unknown: '#64748b', // slate-500
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

export default function Analytics() {
  const [sessions, setSessions] = useState([])
  const [selectedSessionId, setSelectedSessionId] = useState('')
  const [summaryData, setSummaryData] = useState(null)
  const [attendanceTrend, setAttendanceTrend] = useState(null)
  const [trendError, setTrendError] = useState('')
  const [loadingTrend, setLoadingTrend] = useState(true)
  const [loadingSessions, setLoadingSessions] = useState(true)
  const [loadingSummary, setLoadingSummary] = useState(false)
  const [error, setError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  // Load list of sessions
  const loadSessions = useCallback(async (signal) => {
    try {
      setLoadingSessions(true)
      setError('')

      const fetchedSessions = await getHistorySessions(50, 0, { signal })
      if (signal?.aborted) return
      setSessions(fetchedSessions)

      if (fetchedSessions.length > 0) {
        setSelectedSessionId((currentId) => {
          const exists = fetchedSessions.some((s) => s.session_id === currentId)
          return exists ? currentId : fetchedSessions[0].session_id
        })
      } else {
        setSelectedSessionId('')
        setSummaryData(null)
      }
    } catch (err) {
      if (signal?.aborted) return
      console.error('Failed to load sessions:', err)
      setSessions([])
      setSelectedSessionId('')
      setSummaryData(null)
      setError(
        'Unable to load analytics. Please check that the backend is running.',
      )
    } finally {
      if (!signal?.aborted) setLoadingSessions(false)
    }
  }, [])

  // Load summary for selected session
  const loadSummary = useCallback(async (sessionId, signal) => {
    if (!sessionId) {
      setSummaryData(null)
      setLoadingSummary(false)
      return
    }

    try {
      setLoadingSummary(true)
      setError('')

      const summary = await getSessionSummary(sessionId, { signal })
      if (signal?.aborted) return
      setSummaryData(summary)
    } catch (err) {
      if (signal?.aborted) return
      console.error(`Failed to load summary for session ${sessionId}:`, err)
      const detail =
        err?.response?.data?.detail ||
        'Unable to load session analytics. Please check that the backend is running.'
      setError(detail)
    } finally {
      if (!signal?.aborted) setLoadingSummary(false)
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    loadSessions(controller.signal)
    return () => controller.abort()
  }, [loadSessions, refreshKey])

  useEffect(() => {
    const controller = new AbortController()
    loadSummary(selectedSessionId, controller.signal)
    return () => controller.abort()
  }, [selectedSessionId, loadSummary, refreshKey])

  useEffect(() => {
    const controller = new AbortController()
    const toDate = new Date().toISOString().slice(0, 10)
    const from = new Date()
    from.setUTCDate(from.getUTCDate() - 29)
    const fromDate = from.toISOString().slice(0, 10)

    async function loadTrend() {
      setLoadingTrend(true)
      setTrendError('')
      try {
        const data = await getClassroomAttendance({
          fromDate,
          toDate,
          limit: 1,
          signal: controller.signal,
        })
        if (!controller.signal.aborted) setAttendanceTrend(data)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setTrendError(
            requestError?.response?.data?.detail ||
              'Unable to load the 30-day attendance trend.',
          )
        }
      } finally {
        if (!controller.signal.aborted) setLoadingTrend(false)
      }
    }

    loadTrend()
    return () => controller.abort()
  }, [refreshKey])

  const handleRefresh = () => setRefreshKey((current) => current + 1)

  const selectedSession = useMemo(() => {
    return (
      sessions.find((s) => s.session_id === selectedSessionId) ||
      summaryData?.session ||
      null
    )
  }, [sessions, selectedSessionId, summaryData])

  const stats = useMemo(() => {
    return summaryData?.statistics || null
  }, [summaryData])

  const statusBadge = useMemo(() => {
    return getStatusBadge(selectedSession?.status)
  }, [selectedSession])

  const chartData = useMemo(() => {
    if (!stats || stats.attention_records === 0) {
      return []
    }

    return [
      {
        name: 'Attentive',
        value: stats.attentive_count,
        percentage: stats.attentive_percentage,
        color: ATTENTION_COLORS.attentive,
      },
      {
        name: 'Not Attentive',
        value: stats.not_attentive_count,
        percentage: stats.not_attentive_percentage,
        color: ATTENTION_COLORS.notAttentive,
      },
      {
        name: 'Unknown',
        value: stats.unknown_count,
        percentage: stats.unknown_percentage,
        color: ATTENTION_COLORS.unknown,
      },
    ]
  }, [stats])

  const isInitialLoading = loadingSessions && sessions.length === 0

  return (
    <div className="mx-auto max-w-[1600px] p-4 sm:p-6 lg:p-8 space-y-6">
      {/* 1. Page Header */}
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-blue-400">
            <BarChart3 size={15} />
            Teacher Dashboard
          </div>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-white sm:text-3xl">
            Analytics
          </h1>
          <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-slate-400">
            Analyze classroom attendance and attention performance.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Session Selector */}
          {sessions.length > 0 && (
            <div className="relative">
              <select
                aria-label="Select classroom session"
                value={selectedSessionId}
                onChange={(e) => setSelectedSessionId(e.target.value)}
                disabled={loadingSessions || loadingSummary}
                className="appearance-none rounded-xl border border-slate-800 bg-[#0d1424] py-2.5 pl-3.5 pr-9 text-xs font-medium text-slate-200 transition focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
              >
                {sessions.map((s) => (
                  <option key={s.session_id} value={s.session_id}>
                    {s.session_id} ({s.status})
                  </option>
                ))}
              </select>
              <ChevronDown
                size={14}
                className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"
              />
            </div>
          )}

          {/* Selected Session Status Badge */}
          {selectedSession && (
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${statusBadge.pillClass}`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${statusBadge.dotClass}`} />
              {statusBadge.label}
            </span>
          )}

          {/* Refresh Button */}
          <button
            type="button"
            onClick={handleRefresh}
            disabled={loadingSessions || loadingSummary}
            className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/80 px-4 py-2.5 text-xs font-medium text-slate-300 transition hover:border-slate-700 hover:bg-slate-800 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCw
              size={14}
              className={loadingSessions || loadingSummary ? 'animate-spin' : ''}
            />
            <span>Refresh</span>
          </button>
        </div>
      </header>

      {/* 8. Error Banner */}
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

      {/* 6. Empty State (No sessions exist) */}
      {!isInitialLoading && sessions.length === 0 && !error && (
        <div className="surface flex min-h-[380px] flex-col items-center justify-center p-8 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-800 bg-slate-900/90 text-blue-400">
            <BarChart3 size={28} />
          </div>
          <h2 className="mt-4 text-lg font-bold text-white">
            No analytics available
          </h2>
          <p className="mt-2 max-w-md text-sm text-slate-400">
            Start a classroom session and collect attendance/attention data to
            see analytics.
          </p>
          <button
            type="button"
            onClick={handleRefresh}
            className="mt-6 flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-4 py-2 text-xs font-medium text-slate-300 transition hover:bg-slate-800 hover:text-white"
          >
            <RefreshCw size={14} />
            Check again
          </button>
        </div>
      )}

      {/* When sessions exist or during loading */}
      {(sessions.length > 0 || isInitialLoading) && (
        <>
          <section className="surface p-5 sm:p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-white">Attendance trend</h2>
                <p className="mt-1 text-xs text-slate-400">
                  Persisted present and absent records by UTC date over the last 30 days.
                </p>
              </div>
              <span className="text-xs text-slate-500">
                {attendanceTrend
                  ? `${attendanceTrend.from_date} – ${attendanceTrend.to_date} UTC`
                  : 'Last 30 days'}
              </span>
            </div>
            {trendError ? (
              <p role="alert" className="mt-5 text-sm text-red-300">{trendError}</p>
            ) : loadingTrend ? (
              <p className="mt-5 text-sm text-slate-400">Loading attendance history…</p>
            ) : attendanceTrend?.daily_trend.length ? (
              <div className="mt-5 h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={attendanceTrend.daily_trend}>
                    <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                    <YAxis allowDecimals={false} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="present_count" name="Present" fill="#34d399" />
                    <Bar dataKey="absent_count" name="Absent" fill="#fb7185" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="mt-5 text-sm text-slate-500">No persisted attendance records in this period.</p>
            )}
          </section>

          {/* 2. Summary Cards Grid */}
          <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <SummaryCard
              icon={<Users size={18} />}
              label="Total Students"
              value={loadingSummary ? null : stats ? stats.unique_students : '—'}
              description="Unique students identified"
              iconClass="bg-blue-500/10 text-blue-400"
            />
            <SummaryCard
              icon={<ClipboardCheck size={18} />}
              label="Attendance Records"
              value={loadingSummary ? null : stats ? stats.attendance_records : '—'}
              description="Session attendance logs"
              iconClass="bg-indigo-500/10 text-indigo-400"
            />
            <SummaryCard
              icon={<Activity size={18} />}
              label="Attention Records"
              value={loadingSummary ? null : stats ? stats.attention_records : '—'}
              description="Captured frame detections"
              iconClass="bg-purple-500/10 text-purple-400"
            />
            <SummaryCard
              icon={<CheckCircle2 size={18} />}
              label="Attentive %"
              value={
                loadingSummary
                  ? null
                  : stats ? `${stats.attentive_percentage}%` : '—'
              }
              description={stats ? `${stats.attentive_count} attentive records` : 'No summary available'}
              iconClass="bg-emerald-500/10 text-emerald-400"
            />
            <SummaryCard
              icon={<AlertTriangle size={18} />}
              label="Not Attentive %"
              value={
                loadingSummary
                  ? null
                  : stats ? `${stats.not_attentive_percentage}%` : '—'
              }
              description={stats ? `${stats.not_attentive_count} inattentive records` : 'No summary available'}
              iconClass="bg-rose-500/10 text-rose-400"
            />
            <SummaryCard
              icon={<HelpCircle size={18} />}
              label="Unknown %"
              value={
                loadingSummary
                  ? null
                  : stats ? `${stats.unknown_percentage}%` : '—'
              }
              description={stats ? `${stats.unknown_count} unclassified records` : 'No summary available'}
              iconClass="bg-slate-500/10 text-slate-400"
            />
          </section>

          {/* Middle Row: Attention Distribution Chart + Selected Session Details */}
          <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* 3. Attention Distribution Chart (7 cols on lg) */}
            <div className="surface p-5 sm:p-6 lg:col-span-7 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-base font-semibold text-white">
                      Attention Distribution
                    </h2>
                    <p className="mt-1 text-xs text-slate-400">
                      Distribution of student attentiveness states during this session.
                    </p>
                  </div>
                  <span className="rounded-lg border border-slate-800 bg-slate-900/60 px-2.5 py-1 text-[11px] font-medium text-slate-400">
                    Real-time Summary
                  </span>
                </div>

                {/* Chart Area */}
                <div className="mt-6 flex flex-col items-center justify-center min-h-[260px]">
                  {loadingSummary ? (
                    <div className="flex h-[260px] w-full flex-col items-center justify-center gap-3">
                      <div className="h-40 w-40 rounded-full border-4 border-slate-800 border-t-blue-500 animate-spin" />
                      <p className="text-xs text-slate-500">Loading chart data...</p>
                    </div>
                  ) : chartData.length > 0 ? (
                    <div className="w-full">
                      <div className="relative h-[240px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={chartData}
                              cx="50%"
                              cy="50%"
                              innerRadius={65}
                              outerRadius={95}
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
                        {/* Center donut label */}
                        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
                          <span className="text-2xl font-bold tracking-tight text-white">
                            {stats?.attentive_percentage ?? '—'}{stats ? '%' : ''}
                          </span>
                          <span className="text-[10px] font-medium uppercase tracking-wider text-slate-400">
                            Attentive
                          </span>
                        </div>
                      </div>

                      {/* Chart Legend */}
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
                        No attention records captured
                      </p>
                      <p className="mt-1 max-w-xs text-xs text-slate-500">
                        This session does not have attention records logged yet.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* 5. Selected Session Analytics Detail (5 cols on lg) */}
            <div className="surface p-5 sm:p-6 lg:col-span-5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <h2 className="text-base font-semibold text-white">
                    Session Overview
                  </h2>
                  {selectedSession && (
                    <span
                      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${statusBadge.pillClass}`}
                    >
                      <span className={`h-1.5 w-1.5 rounded-full ${statusBadge.dotClass}`} />
                      {statusBadge.label}
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-slate-400">
                  Metadata and breakdown for the currently selected session.
                </p>

                {/* Session Attributes List */}
                <div className="mt-5 space-y-3">
                  <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                    <p className="text-[11px] font-medium uppercase tracking-wider text-slate-500">
                      Session Identifier
                    </p>
                    <p className="mt-1 font-mono text-xs font-semibold text-blue-300 break-all">
                      {selectedSession?.session_id || '—'}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                      <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
                        <Calendar size={13} />
                        <span>Started</span>
                      </div>
                      <p className="mt-1 text-xs font-medium text-slate-200 truncate">
                        {formatDateTime(selectedSession?.started_at)}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                      <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
                        <Clock size={13} />
                        <span>Duration</span>
                      </div>
                      <p className="mt-1 text-xs font-medium text-slate-200">
                        {formatDuration(selectedSession?.duration_seconds)}
                      </p>
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                    <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
                      <Calendar size={13} />
                      <span>Ended</span>
                    </div>
                    <p className="mt-1 text-xs font-medium text-slate-200 truncate">
                      {selectedSession?.ended_at
                        ? formatDateTime(selectedSession.ended_at)
                        : selectedSession?.status === 'ACTIVE'
                          ? 'Session currently in progress'
                          : '—'}
                    </p>
                  </div>

                  {/* Student IDs Badge Cloud */}
                  <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-3">
                    <div className="flex items-center justify-between">
                      <p className="text-[11px] font-medium uppercase tracking-wider text-slate-500">
                        Student Check-ins
                      </p>
                      <span className="text-[11px] font-medium text-slate-400">
                        {stats?.student_ids?.length || 0} enrolled
                      </span>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {stats?.student_ids && stats.student_ids.length > 0 ? (
                        stats.student_ids.map((id) => (
                          <span
                            key={id}
                            className="rounded-lg border border-blue-500/20 bg-blue-500/10 px-2 py-0.5 font-mono text-[11px] font-medium text-blue-300"
                          >
                            {id}
                          </span>
                        ))
                      ) : (
                        <span className="text-xs text-slate-500">
                          No student IDs recorded for this session.
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* 4. Session History Table */}
          <section className="surface p-5 sm:p-6">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-base font-semibold text-white">
                  Session History
                </h2>
                <p className="text-xs text-slate-400">
                  Select any session to view its complete attendance and attention analytics.
                </p>
              </div>
              <span className="text-xs text-slate-500">
                {sessions.length} recorded session{sessions.length === 1 ? '' : 's'}
              </span>
            </div>

            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-500">
                    <th className="py-3 px-3">Session</th>
                    <th className="py-3 px-3">Status</th>
                    <th className="py-3 px-3">Started</th>
                    <th className="py-3 px-3">Ended</th>
                    <th className="py-3 px-3">Duration</th>
                    <th className="py-3 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {sessions.map((sess) => {
                    const isSelected = sess.session_id === selectedSessionId
                    const badge = getStatusBadge(sess.status)

                    return (
                      <tr
                        key={sess.session_id}
                        onClick={() => setSelectedSessionId(sess.session_id)}
                        className={`cursor-pointer transition-colors ${
                          isSelected
                            ? 'bg-blue-500/10 hover:bg-blue-500/15'
                            : 'hover:bg-slate-900/60'
                        }`}
                      >
                        <td className="py-3 px-3">
                          <div className="flex items-center gap-2">
                            {isSelected && (
                              <span className="h-1.5 w-1.5 rounded-full bg-blue-400 shrink-0" />
                            )}
                            <span
                              className={`font-mono font-medium ${
                                isSelected ? 'text-blue-300' : 'text-white'
                              }`}
                            >
                              {sess.session_id}
                            </span>
                          </div>
                        </td>
                        <td className="py-3 px-3">
                          <span
                            className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${badge.pillClass}`}
                          >
                            <span className={`h-1.5 w-1.5 rounded-full ${badge.dotClass}`} />
                            {badge.label}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-slate-300 whitespace-nowrap">
                          {formatDateTime(sess.started_at)}
                        </td>
                        <td className="py-3 px-3 text-slate-400 whitespace-nowrap">
                          {sess.ended_at
                            ? formatDateTime(sess.ended_at)
                            : sess.status === 'ACTIVE'
                              ? 'In progress'
                              : '—'}
                        </td>
                        <td className="py-3 px-3 font-mono text-slate-300 whitespace-nowrap">
                          {formatDuration(sess.duration_seconds)}
                        </td>
                        <td className="py-3 px-3 text-right">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation()
                              setSelectedSessionId(sess.session_id)
                            }}
                            className={`rounded-lg px-2.5 py-1 text-xs font-medium transition ${
                              isSelected
                                ? 'bg-blue-500 text-white'
                                : 'border border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-700 hover:text-white'
                            }`}
                          >
                            {isSelected ? 'Selected' : 'View'}
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
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
    <div className="surface p-5 transition duration-200 hover:border-slate-700 flex flex-col justify-between">
      <div className="flex items-start justify-between gap-4">
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-xl ${iconClass}`}
        >
          {icon}
        </div>
        <span className="rounded-full border border-slate-800 bg-slate-900/60 px-2 py-0.5 text-[10px] font-medium text-slate-400">
          Metric
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
