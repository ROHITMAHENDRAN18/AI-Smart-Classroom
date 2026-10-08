import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  Clock3,
  Mail,
  RefreshCw,
  ShieldCheck,
  UserCheck,
  Users,
} from 'lucide-react'

import { getClassroomOverview } from '../services/classroomService'

const classroomId = import.meta.env.VITE_DEFAULT_CLASSROOM_ID

export default function ClassroomOverview() {
  const [overview, setOverview] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')

  const loadOverview = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true)
      } else {
        setLoading(true)
      }

      setError('')

      const data = await getClassroomOverview(classroomId)

      setOverview(data)
    } catch (requestError) {
      console.error('Failed to load classroom overview:', requestError)

      const message =
        requestError?.response?.data?.detail ||
        requestError?.message ||
        'Unable to load classroom overview.'

      setError(message)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    loadOverview()
  }, [loadOverview])

  const sessionStatus = useMemo(() => {
    if (!overview?.active_session) {
      return {
        label: 'No active session',
        className:
          'border-slate-800 bg-slate-900/60 text-slate-400',
        dotClass: 'status-dot-neutral',
      }
    }

    if (overview.active_session.status === 'ACTIVE') {
      return {
        label: 'Session active',
        className:
          'border-emerald-500/20 bg-emerald-500/5 text-emerald-400',
        dotClass: 'status-dot-success',
      }
    }

    return {
      label: overview.active_session.status,
      className:
        'border-slate-800 bg-slate-900/60 text-slate-400',
      dotClass: 'status-dot-neutral',
    }
  }, [overview])

  if (loading) {
    return <ClassroomLoading />
  }

  if (error && !overview) {
    return (
      <div className="mx-auto max-w-[1600px] p-4 sm:p-6 lg:p-8">
        <ErrorState
          message={error}
          onRetry={() => loadOverview()}
        />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-[1600px] p-4 sm:p-6 lg:p-8">
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm font-medium text-blue-400">
            Classroom overview
          </p>

          <h2 className="mt-1 text-2xl font-bold tracking-tight text-white sm:text-3xl">
            {overview.classroom_name}
          </h2>

          <p className="mt-2 text-sm text-slate-400">
            {overview.classroom_code} · Section {overview.section} · Year{' '}
            {overview.year}
          </p>
        </div>

        <button
          type="button"
          onClick={() => loadOverview(true)}
          disabled={refreshing}
          className="flex w-fit items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/70 px-4 py-2.5 text-sm font-medium text-slate-300 transition hover:border-slate-700 hover:bg-slate-800 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw
            size={16}
            className={refreshing ? 'animate-spin' : ''}
          />

          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {error && (
        <div className="mb-5 flex items-center gap-3 rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-sm text-amber-300">
          <AlertCircle size={17} />
          <span>{error}</span>
        </div>
      )}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          icon={<Users size={19} />}
          label="Total Students"
          value={overview.total_students}
          description="Classroom members"
          iconClass="bg-blue-500/10 text-blue-400"
        />

        <StatCard
          icon={<UserCheck size={19} />}
          label="Active Members"
          value={overview.active_students}
          description="Currently active members"
          iconClass="bg-emerald-500/10 text-emerald-400"
        />

        <StatCard
          icon={<BookOpen size={19} />}
          label="Classroom"
          value={overview.classroom_code}
          description={overview.classroom_name}
          iconClass="bg-cyan-500/10 text-cyan-400"
        />

        <StatCard
          icon={<Clock3 size={19} />}
          label="Session"
          value={overview.active_session ? 'ACTIVE' : 'IDLE'}
          description={
            overview.active_session
              ? 'An active session exists'
              : 'No active session'
          }
          iconClass="bg-violet-500/10 text-violet-400"
        />
      </section>

      <section className="mt-6 grid gap-6 xl:grid-cols-[1.4fr_0.6fr]">
        <div className="surface overflow-hidden">
          <div className="flex flex-col gap-3 border-b border-slate-800 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
            <div>
              <h3 className="text-base font-semibold text-white">
                Students
              </h3>

              <p className="mt-1 text-xs text-slate-500">
                Students registered in this classroom
              </p>
            </div>

            <div className="flex w-fit items-center gap-2 rounded-full border border-slate-800 bg-slate-900/60 px-3 py-1.5">
              <Users size={13} className="text-slate-500" />

              <span className="text-xs font-medium text-slate-400">
                {overview.students.length} student
                {overview.students.length === 1 ? '' : 's'}
              </span>
            </div>
          </div>

          <div className="overflow-x-auto">
            {overview.students.length === 0 ? (
              <EmptyStudents />
            ) : (
              <table className="w-full min-w-[650px]">
                <thead>
                  <tr className="border-b border-slate-800 text-left">
                    <th className="px-5 py-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-600 sm:px-6">
                      Student
                    </th>

                    <th className="px-5 py-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-600">
                      Student ID
                    </th>

                    <th className="px-5 py-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-600">
                      Section
                    </th>

                    <th className="px-5 py-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-600">
                      Face
                    </th>

                    <th className="px-5 py-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-600">
                      Status
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {overview.students.map((student) => (
                    <StudentRow
                      key={student.student_id}
                      student={student}
                    />
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="surface p-5 sm:p-6">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="text-base font-semibold text-white">
                Classroom
              </h3>

              <p className="mt-1 text-xs text-slate-500">
                Registered classroom information
              </p>
            </div>

            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
              <BookOpen size={19} />
            </div>
          </div>

          <div className="mt-6 space-y-4">
            <InfoRow
              label="Classroom"
              value={overview.classroom_code}
            />

            <InfoRow
              label="Department"
              value={overview.department}
            />

            <InfoRow
              label="Year"
              value={String(overview.year)}
            />

            <InfoRow
              label="Section"
              value={overview.section}
            />

            <InfoRow
              label="Teacher ID"
              value={String(overview.teacher_id)}
            />

            <InfoRow
              label="Status"
              value={
                overview.is_active
                  ? 'Active classroom'
                  : 'Inactive classroom'
              }
              valueClass={
                overview.is_active
                  ? 'text-emerald-400'
                  : 'text-red-400'
              }
            />
          </div>
        </div>
      </section>

      <section className="mt-6 surface p-5 sm:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-base font-semibold text-white">
              Current session
            </h3>

            <p className="mt-1 text-xs text-slate-500">
              Session information from the classroom session system
            </p>
          </div>

          <div
            className={`flex w-fit items-center gap-2 rounded-full border px-3 py-1.5 ${sessionStatus.className}`}
          >
            <span className={`status-dot ${sessionStatus.dotClass}`} />

            <span className="text-xs font-semibold">
              {sessionStatus.label}
            </span>
          </div>
        </div>

        {overview.active_session ? (
          <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <SessionInfo
              label="Session ID"
              value={overview.active_session.session_id}
            />

            <SessionInfo
              label="Status"
              value={overview.active_session.status}
            />

            <SessionInfo
              label="Session Record"
              value={String(overview.active_session.id)}
            />

            <SessionInfo
              label="Classroom ID"
              value={String(overview.active_session.classroom_id)}
            />
          </div>
        ) : (
          <div className="mt-5 rounded-xl border border-dashed border-slate-800 bg-slate-950/40 px-5 py-8 text-center">
            <Clock3
              size={22}
              className="mx-auto text-slate-600"
            />

            <p className="mt-3 text-sm font-medium text-slate-400">
              No active classroom session
            </p>

            <p className="mt-1 text-xs text-slate-600">
              Session controls will be connected in the session
              control phase.
            </p>
          </div>
        )}
      </section>
    </div>
  )
}

function StatCard({
  icon,
  label,
  value,
  description,
  iconClass,
}) {
  return (
    <div className="surface p-5 transition duration-200 hover:border-slate-700">
      <div
        className={`flex h-10 w-10 items-center justify-center rounded-xl ${iconClass}`}
      >
        {icon}
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

function StudentRow({ student }) {
  return (
    <tr className="border-b border-slate-800/70 transition hover:bg-slate-900/40">
      <td className="px-5 py-4 sm:px-6">
        <div>
          <p className="text-sm font-medium text-slate-200">
            {student.name}
          </p>

          <div className="mt-1 flex items-center gap-1.5 text-xs text-slate-600">
            <Mail size={11} />
            <span>{student.email || 'No email'}</span>
          </div>
        </div>
      </td>

      <td className="px-5 py-4 text-sm font-medium text-slate-400">
        {student.student_id}
      </td>

      <td className="px-5 py-4 text-sm text-slate-400">
        {student.section}
      </td>

      <td className="px-5 py-4">
        {student.face_registered ? (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/15 bg-emerald-500/5 px-2.5 py-1 text-[11px] font-medium text-emerald-400">
            <ShieldCheck size={12} />
            Registered
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/15 bg-amber-500/5 px-2.5 py-1 text-[11px] font-medium text-amber-400">
            Not registered
          </span>
        )}
      </td>

      <td className="px-5 py-4">
        {student.is_active ? (
          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-400">
            <span className="status-dot status-dot-success" />
            Active
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500">
            <span className="status-dot status-dot-neutral" />
            Inactive
          </span>
        )}
      </td>
    </tr>
  )
}

function InfoRow({
  label,
  value,
  valueClass = 'text-slate-300',
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-800/70 pb-3">
      <span className="text-xs text-slate-600">{label}</span>

      <span
        className={`max-w-[65%] text-right text-xs font-medium ${valueClass}`}
      >
        {value}
      </span>
    </div>
  )
}

function SessionInfo({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-4">
      <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-600">
        {label}
      </p>

      <p className="mt-2 truncate text-sm font-medium text-slate-300">
        {value}
      </p>
    </div>
  )
}

function ClassroomLoading() {
  return (
    <div className="mx-auto max-w-[1600px] animate-pulse p-4 sm:p-6 lg:p-8">
      <div className="h-4 w-36 rounded bg-slate-800" />
      <div className="mt-3 h-8 w-72 rounded bg-slate-800" />
      <div className="mt-2 h-4 w-64 rounded bg-slate-900" />

      <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            key={index}
            className="h-32 rounded-2xl border border-slate-800 bg-slate-900/50"
          />
        ))}
      </div>

      <div className="mt-6 h-96 rounded-2xl border border-slate-800 bg-slate-900/50" />
    </div>
  )
}

function ErrorState({ message, onRetry }) {
  return (
    <div className="flex min-h-[420px] items-center justify-center">
      <div className="max-w-md text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-red-500/10 text-red-400">
          <AlertCircle size={22} />
        </div>

        <h2 className="mt-4 text-base font-semibold text-white">
          Unable to load classroom
        </h2>

        <p className="mt-2 text-sm leading-6 text-slate-500">
          {message}
        </p>

        <button
          type="button"
          onClick={onRetry}
          className="mt-5 inline-flex items-center gap-2 rounded-xl bg-blue-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-400"
        >
          <RefreshCw size={16} />
          Try again
        </button>
      </div>
    </div>
  )
}

function EmptyStudents() {
  return (
    <div className="px-6 py-16 text-center">
      <Users size={24} className="mx-auto text-slate-600" />

      <p className="mt-3 text-sm font-medium text-slate-400">
        No students found
      </p>

      <p className="mt-1 text-xs text-slate-600">
        No active classroom members are currently registered.
      </p>
    </div>
  )
}
