
import { useCallback, useEffect, useState } from 'react'
import { RefreshCw, Users } from 'lucide-react'
import { getStudents } from '../services/reports'

function getStudentId(student) {
  return (
    student.student_id ??
    student.studentId ??
    student.roll_number ??
    student.roll_no ??
    student.id ??
    '—'
  )
}

function getStudentName(student) {
  return (
    student.name ??
    student.full_name ??
    student.student_name ??
    student.username ??
    'Unnamed student'
  )
}

function normalizeStudents(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.students)) return data.students
  if (Array.isArray(data?.items)) return data.items
  if (Array.isArray(data?.data)) return data.data
  return []
}

export default function Students() {
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadStudents = useCallback(async () => {
    setLoading(true)
    setError('')

    try {
      const response = await getStudents()
      setStudents(normalizeStudents(response))
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          'Unable to load students. Check the backend connection.'
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadStudents()
  }, [loadStudents])

  return (
    <main className="space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm text-sky-400">Classroom management</p>
          <h1 className="mt-1 text-2xl font-bold text-white">Students</h1>
          <p className="mt-2 text-sm text-slate-400">
            View students returned by the classroom API.
          </p>
        </div>

        <button
          type="button"
          onClick={loadStudents}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-4 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-sky-500/10 p-3 text-sky-400">
            <Users size={22} />
          </div>
          <div>
            <p className="text-sm text-slate-400">Registered students</p>
            <p className="text-2xl font-bold text-white">
              {loading ? '…' : students.length}
            </p>
          </div>
        </div>
      </section>

      {loading && (
        <p className="text-sm text-slate-400">Loading students…</p>
      )}

      {!loading && error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
          {error}
        </div>
      )}

      {!loading && !error && students.length === 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-8 text-center">
          <Users className="mx-auto mb-3 text-slate-500" size={32} />
          <h2 className="font-semibold text-white">No students found</h2>
          <p className="mt-2 text-sm text-slate-400">
            The API returned no student records. Check whether students have
            been registered in the database.
          </p>
        </div>
      )}

      {!loading && !error && students.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-slate-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900 text-slate-400">
              <tr>
                <th className="px-5 py-3 font-medium">Student ID</th>
                <th className="px-5 py-3 font-medium">Name</th>
                <th className="px-5 py-3 font-medium">Email</th>
              </tr>
            </thead>
            <tbody>
              {students.map((student, index) => (
                <tr
                  key={String(getStudentId(student)) + '-' + index}
                  className="border-t border-slate-800 text-slate-200"
                >
                  <td className="px-5 py-4">{getStudentId(student)}</td>
                  <td className="px-5 py-4">{getStudentName(student)}</td>
                  <td className="px-5 py-4">
                    {student.email ?? student.email_address ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  )
}