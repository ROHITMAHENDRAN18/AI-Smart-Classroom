import { useCallback, useEffect, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Clock3,
  RefreshCw,
  Users,
} from 'lucide-react'
import { Link } from 'react-router-dom'

import { getClassroomOverview } from '../services/classroomService'

const classroomId = import.meta.env.VITE_DEFAULT_CLASSROOM_ID

export default function Dashboard() {
  const [overview, setOverview] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadOverview = useCallback(async () => {
    try {
      setLoading(true)
      setError('')

      const data = await getClassroomOverview(classroomId)

      setOverview(data)
    } catch (requestError) {
      console.error('Failed to load dashboard overview:', requestError)

      const message =
        requestError?.response?.data?.detail ||
        requestError?.message ||
        'Unable to load classroom data.'

      setError(message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadOverview()
  }, [loadOverview])

  return (
    <div className="mx-auto max-w-[1600px] p-4 sm:p-6 lg:p-8">
      <section className="mb-6">
        <p className="text-sm font-medium text-blue-400">
          Classroom overview
        </p>

        <h2 className="mt-1 text-2xl font-bold tracking-tight text-white sm:text-3xl">
          {overview?.classroom_name || 'Your classroom'}
        </h2>

        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
          Monitor classroom activity, students, attendance, alerts,
          analytics, and session performance from one workspace.
        </p>
      </section>

      {error && (
        <div className="mb-5 flex flex-col gap-3 rounded-xl border border-red-500/20 bg-red-500/5 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3 text-sm text-red-300">
            <AlertTriangle size={17} />
            <span>{error}</span>
          </div>

          <button
            type="button"
            onClick={loadOverview}
            className="flex w-fit items-center gap-2 rounded-lg border border-red-500/20 px-3 py-2 text-xs font-semibold text-red-300 transition hover:bg-red-500/10"
          >
            <RefreshCw size={14} />
            Retry
          </button>
        </div>
      )}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          icon={<Users size={19} />}
          label="Class Students"
          value={
            loading ? '...' : overview?.total_students ?? '—'
          }
          description="Registered classroom members"
          iconClass="bg-blue-500/10 text-blue-400"
        />

        <MetricCard
          icon={<Activity size={19} />}
          label="Attention"
          value="—"
          description="Live AI attention metric"
          iconClass="bg-emerald-500/10 text-emerald-400"
          pending
        />

        <MetricCard
          icon={<CheckCircle2 size={19} />}
          label="Classroom"
          value={
            loading
              ? '...'
              : overview?.classroom_code || '—'
          }
          description={
            overview?.classroom_name || 'Classroom information'
          }
          iconClass="bg-cyan-500/10 text-cyan-400"
        />

        <MetricCard
          icon={<AlertTriangle size={19} />}
          label="Alerts"
          value="—"
          description="Live AI alerts"
          iconClass="bg-amber-500/10 text-amber-400"
          pending
        />
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.5fr_1fr]">
        <div className="surface min-h-[360px] p-5 sm:p-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h3 className="text-base font-semibold text-white">
                Classroom
              </h3>

              <p className="mt-1 text-xs text-slate-500">
                Registered classroom overview
              </p>
            </div>

            <Link
              to="/dashboard/classroom"
              className="flex w-fit items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-xs font-semibold text-slate-400 transition hover:border-slate-700 hover:bg-slate-800 hover:text-white"
            >
              View classroom
              <ArrowRight size={14} />
            </Link>
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <OverviewItem
              icon={<BookOpen size={17} />}
              label="Classroom"
              value={overview?.classroom_name || 'Loading...'}
            />

            <OverviewItem
              icon={<Users size={17} />}
              label="Students"
              value={
                loading
                  ? 'Loading...'
                  : `${overview?.total_students ?? 0} registered`
              }
            />

            <OverviewItem
              icon={<CheckCircle2 size={17} />}
              label="Classroom status"
              value={
                overview?.is_active
                  ? 'Active'
                  : 'Inactive'
              }
              valueClass={
                overview?.is_active
                  ? 'text-emerald-400'
                  : 'text-red-400'
              }
            />

            <OverviewItem
              icon={<Clock3 size={17} />}
              label="Session"
              value={
                overview?.active_session
                  ? overview.active_session.status
                  : 'No active session'
              }
              valueClass={
                overview?.active_session
                  ? 'text-emerald-400'
                  : 'text-slate-500'
              }
            />
          </div>
        </div>

        <div className="surface p-5 sm:p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold text-white">
                Session status
              </h3>

              <p className="mt-1 text-xs text-slate-500">
                Current classroom session
              </p>
            </div>

            <Clock3 size={18} className="text-slate-500" />
          </div>

          <div className="mt-6 rounded-xl border border-slate-800 bg-slate-950/40 p-5">
            {overview?.active_session ? (
              <div className="flex items-start gap-3">
                <span className="mt-1 status-dot status-dot-success" />

                <div className="min-w-0">
                  <p className="text-sm font-semibold text-emerald-400">
                    Active session
                  </p>

                  <p className="mt-1 truncate text-xs text-slate-600">
                    {overview.active_session.session_id}
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex items-start gap-3">
                <span className="mt-1 status-dot status-dot-neutral" />

                <div>
                  <p className="text-sm font-semibold text-slate-400">
                    No active session
                  </p>

                  <p className="mt-1 text-xs text-slate-600">
                    Session controls will be connected later.
                  </p>
                </div>
              </div>
            )}
          </div>

          <Link
            to="/dashboard/classroom"
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-slate-800 bg-slate-900/50 px-4 py-3 text-sm font-semibold text-slate-400 transition hover:border-slate-700 hover:bg-slate-800 hover:text-white"
          >
            Open classroom
            <ArrowRight size={16} />
          </Link>
        </div>
      </section>
    </div>
  )
}

function MetricCard({
  icon,
  label,
  value,
  description,
  iconClass,
  pending = false,
}) {
  return (
    <div className="surface p-5 transition duration-200 hover:border-slate-700">
      <div className="flex items-start justify-between gap-4">
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-xl ${iconClass}`}
        >
          {icon}
        </div>

        {pending ? (
          <span className="rounded-full border border-slate-800 bg-slate-900/60 px-2 py-1 text-[10px] font-medium text-slate-600">
            AI pending
          </span>
        ) : (
          <span className="rounded-full border border-emerald-500/10 bg-emerald-500/5 px-2 py-1 text-[10px] font-medium text-emerald-500">
            Live data
          </span>
        )}
      </div>

      <p className="mt-5 text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </p>

      <p className="mt-1 truncate text-2xl font-bold tracking-tight text-white">
        {value}
      </p>

      <p className="mt-1 truncate text-xs text-slate-600">
        {description}
      </p>
    </div>
  )
}

function OverviewItem({
  icon,
  label,
  value,
  valueClass = 'text-slate-300',
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
      <div className="flex items-center gap-2 text-slate-600">
        {icon}
        <span className="text-xs">{label}</span>
      </div>

      <p
        className={`mt-3 truncate text-sm font-semibold ${valueClass}`}
      >
        {value}
      </p>
    </div>
  )
}
