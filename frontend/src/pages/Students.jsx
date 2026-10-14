
import { useCallback, useEffect, useMemo, useState } from 'react'
import { Check, Pencil, Plus, RefreshCw, UserMinus, UserPlus, Users, X } from 'lucide-react'
import { getStudents } from '../services/reports'
import {
  createClassroomStudent,
  setClassroomStudentActive,
  updateStudent,
} from '../services/classroomDataService'
import {
  notifyClassroomDataChanged,
  subscribeToClassroomDataChanges,
} from '../utils/classroomDataEvents'

const EMPTY_STUDENT_FORM = {
  student_id: '',
  name: '',
  department: '',
  year: '1',
  section: '',
  email: '',
}

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

export default function Students() {
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [newStudent, setNewStudent] = useState(EMPTY_STUDENT_FORM)
  const [editingStudentId, setEditingStudentId] = useState('')
  const [editStudent, setEditStudent] = useState(EMPTY_STUDENT_FORM)
  const [savingAction, setSavingAction] = useState(false)
  const [actionError, setActionError] = useState('')

  const loadStudents = useCallback(async (signal) => {
    setLoading(true)
    setError('')

    try {
      const response = await getStudents({ signal })
      if (!signal?.aborted) setStudents(response)
    } catch (err) {
      if (!signal?.aborted) {
        setStudents([])
        setError(
          err?.response?.data?.detail ||
            err?.message ||
            'Unable to load students. Check the backend connection.'
        )
      }
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }, [])

  async function handleCreateStudent(event) {
    event.preventDefault()
    if (savingAction) return
    setSavingAction(true)
    setActionError('')
    try {
      await createClassroomStudent({
        ...newStudent,
        year: Number(newStudent.year),
        email: newStudent.email.trim() || null,
      })
      setNewStudent(EMPTY_STUDENT_FORM)
      notifyClassroomDataChanged()
    } catch (err) {
      setActionError(
        err?.response?.data?.detail || err?.message || 'Unable to enroll this student.',
      )
    } finally {
      setSavingAction(false)
    }
  }

  function startEditing(student) {
    setActionError('')
    setEditingStudentId(student.student_id)
    setEditStudent({
      student_id: student.student_id,
      name: student.name,
      department: student.department,
      year: String(student.year),
      section: student.section,
      email: student.email ?? '',
    })
  }

  async function handleSaveStudent(event) {
    event.preventDefault()
    if (savingAction || !editingStudentId) return
    setSavingAction(true)
    setActionError('')
    try {
      await updateStudent(editingStudentId, {
        name: editStudent.name,
        department: editStudent.department,
        year: Number(editStudent.year),
        section: editStudent.section,
        email: editStudent.email.trim() || null,
      })
      setEditingStudentId('')
      notifyClassroomDataChanged()
    } catch (err) {
      setActionError(
        err?.response?.data?.detail || err?.message || 'Unable to save student changes.',
      )
    } finally {
      setSavingAction(false)
    }
  }

  async function handleMembershipChange(student) {
    if (savingAction) return
    setSavingAction(true)
    setActionError('')
    try {
      await setClassroomStudentActive(
        student.student_id,
        student.classroom_is_active !== true,
      )
      notifyClassroomDataChanged()
    } catch (err) {
      setActionError(
        err?.response?.data?.detail || err?.message || 'Unable to update classroom enrollment.',
      )
    } finally {
      setSavingAction(false)
    }
  }

  useEffect(() => {
    let controller
    const reload = () => {
      controller?.abort()
      controller = new AbortController()
      loadStudents(controller.signal)
    }
    reload()
    const unsubscribe = subscribeToClassroomDataChanges(reload)
    return () => {
      unsubscribe()
      controller?.abort()
    }
  }, [loadStudents])

  const filteredStudents = useMemo(() => {
    const query = search.trim().toLocaleLowerCase()
    if (!query) return students
    return students.filter((student) =>
      [student.student_id, student.name, student.email, student.department, student.section]
        .filter(Boolean)
        .some((value) => String(value).toLocaleLowerCase().includes(query)),
    )
  }, [search, students])

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
          onClick={() => loadStudents()}
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
              {loading ? '…' : error ? '—' : students.length}
            </p>
          </div>
        </div>
      </section>

      <form
        onSubmit={handleCreateStudent}
        className="rounded-xl border border-slate-800 bg-slate-900/60 p-5"
      >
        <div className="mb-4 flex items-center gap-2">
          <Plus size={18} className="text-sky-400" />
          <h2 className="font-semibold text-white">Enroll a student</h2>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[
            ['student_id', 'Student ID'],
            ['name', 'Name'],
            ['department', 'Department'],
            ['year', 'Year'],
            ['section', 'Section'],
            ['email', 'Email (optional)'],
          ].map(([field, label]) => (
            <label key={field} className="space-y-1 text-xs text-slate-400">
              {label}
              <input
                required={field !== 'email'}
                type={field === 'year' ? 'number' : field === 'email' ? 'email' : 'text'}
                min={field === 'year' ? 1 : undefined}
                max={field === 'year' ? 8 : undefined}
                value={newStudent[field]}
                onChange={(event) =>
                  setNewStudent((current) => ({ ...current, [field]: event.target.value }))
                }
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
              />
            </label>
          ))}
        </div>
        <button
          type="submit"
          disabled={savingAction}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-sky-500 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          <Plus size={16} /> Create and enroll
        </button>
      </form>

      {actionError && (
        <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
          {actionError}
        </div>
      )}

      {loading && (
        <p className="text-sm text-slate-400">Loading students…</p>
      )}

      {!loading && error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
          <p>{error}</p>
          <button type="button" onClick={() => loadStudents()} className="mt-3 underline">
            Retry
          </button>
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
          <div className="border-b border-slate-800 p-4">
            <label htmlFor="student-search" className="sr-only">Search students</label>
            <input
              id="student-search"
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search this classroom…"
              className="w-full max-w-sm rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-sky-500"
            />
            <p className="mt-2 text-xs text-slate-500">
              Showing {filteredStudents.length} of {students.length} classroom students.
            </p>
          </div>
          {filteredStudents.length === 0 ? (
            <p className="p-6 text-sm text-slate-400">No students match this search.</p>
          ) : <table className="w-full text-left text-sm">
            <thead className="bg-slate-900 text-slate-400">
              <tr>
                <th className="px-5 py-3 font-medium">Student ID</th>
                <th className="px-5 py-3 font-medium">Name</th>
                <th className="px-5 py-3 font-medium">Email</th>
                <th className="px-5 py-3 font-medium">Classroom membership</th>
                <th className="px-5 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredStudents.map((student, index) => (
                <tr
                  key={String(getStudentId(student)) + '-' + index}
                  className="border-t border-slate-800 text-slate-200"
                >
                  <td className="px-5 py-4">{getStudentId(student)}</td>
                  <td className="px-5 py-4">
                    {editingStudentId === student.student_id ? (
                      <input aria-label="Student name" value={editStudent.name} onChange={(event) => setEditStudent((current) => ({ ...current, name: event.target.value }))} className="rounded border border-slate-700 bg-slate-950 px-2 py-1" />
                    ) : getStudentName(student)}
                  </td>
                  <td className="px-5 py-4">
                    {editingStudentId === student.student_id ? (
                      <input aria-label="Student email" type="email" value={editStudent.email} onChange={(event) => setEditStudent((current) => ({ ...current, email: event.target.value }))} className="rounded border border-slate-700 bg-slate-950 px-2 py-1" />
                    ) : student.email ?? student.email_address ?? '—'}
                  </td>
                  <td className="px-5 py-4">
                    {student.classroom_is_active === null
                      ? 'Not provided'
                      : student.classroom_is_active ? 'Active' : 'Inactive'}
                  </td>
                  <td className="px-5 py-4">
                    {editingStudentId === student.student_id ? (
                      <form onSubmit={handleSaveStudent} className="flex flex-wrap gap-2">
                        {[
                          ['department', 'Department'],
                          ['year', 'Year'],
                          ['section', 'Section'],
                        ].map(([field, label]) => (
                          <input
                            key={field}
                            aria-label={`Student ${label.toLowerCase()}`}
                            type={field === 'year' ? 'number' : 'text'}
                            min={field === 'year' ? 1 : undefined}
                            max={field === 'year' ? 8 : undefined}
                            value={editStudent[field]}
                            onChange={(event) => setEditStudent((current) => ({ ...current, [field]: event.target.value }))}
                            className="w-24 rounded border border-slate-700 bg-slate-950 px-2 py-1"
                          />
                        ))}
                        <button type="submit" disabled={savingAction} aria-label="Save student" className="rounded p-2 text-emerald-300 hover:bg-slate-800"><Check size={16} /></button>
                        <button type="button" onClick={() => setEditingStudentId('')} aria-label="Cancel edit" className="rounded p-2 text-slate-400 hover:bg-slate-800"><X size={16} /></button>
                      </form>
                    ) : (
                      <div className="flex items-center gap-2">
                        <button type="button" onClick={() => startEditing(student)} className="inline-flex items-center gap-1 rounded border border-slate-700 px-2 py-1 text-xs text-slate-200 hover:bg-slate-800"><Pencil size={13} /> Edit</button>
                        <button type="button" disabled={savingAction} onClick={() => handleMembershipChange(student)} className="inline-flex items-center gap-1 rounded border border-slate-700 px-2 py-1 text-xs text-slate-200 hover:bg-slate-800">
                          {student.classroom_is_active ? <><UserMinus size={13} /> Remove</> : <><UserPlus size={13} /> Enroll</>}
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          }
        </div>
      )}
    </main>
  )
}
