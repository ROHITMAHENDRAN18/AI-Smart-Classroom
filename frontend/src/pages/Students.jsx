
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Camera,
  Check,
  Pencil,
  Plus,
  RefreshCw,
  UserMinus,
  UserPlus,
  Users,
  X,
  RotateCcw,
  Upload,
} from 'lucide-react'
import { getStudents } from '../services/reports'
import {
  createClassroomStudent,
  enrollStudentFace,
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

const MAX_IMAGE_BYTES = 2 * 1024 * 1024
const MAX_IMAGE_PIXELS = 2073600
const MAX_IMAGE_DIMENSION = 1920

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

function getErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail
  return typeof detail === 'string' ? detail : error?.message || fallback
}

function stopCamera(stream) {
  stream?.getTracks().forEach((track) => track.stop())
}

function canvasToBlob(canvas, quality) {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) resolve(blob)
        else reject(new Error('Unable to create a JPEG image. Please try again.'))
      },
      'image/jpeg',
      quality,
    )
  })
}

async function createJpegBlob(video) {
  const sourceWidth = video.videoWidth
  const sourceHeight = video.videoHeight

  if (!sourceWidth || !sourceHeight) {
    throw new Error('The camera is not ready. Wait a moment and try again.')
  }

  const scale = Math.min(
    1,
    MAX_IMAGE_DIMENSION / sourceWidth,
    MAX_IMAGE_DIMENSION / sourceHeight,
    Math.sqrt(MAX_IMAGE_PIXELS / (sourceWidth * sourceHeight)),
  )

  const canvas = document.createElement('canvas')
  canvas.width = Math.max(1, Math.round(sourceWidth * scale))
  canvas.height = Math.max(1, Math.round(sourceHeight * scale))

  const context = canvas.getContext('2d')
  if (!context) throw new Error('Unable to capture the camera image.')

  context.drawImage(video, 0, 0, canvas.width, canvas.height)

  for (const quality of [0.9, 0.8, 0.7, 0.6, 0.5]) {
    const blob = await canvasToBlob(canvas, quality)
    if (blob.size <= MAX_IMAGE_BYTES) return blob
  }

  throw new Error(
    'The captured image is too large. Move closer to the camera and try again.',
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

  const [cameraStudent, setCameraStudent] = useState(null)
  const [cameraStream, setCameraStream] = useState(null)
  const [cameraStarting, setCameraStarting] = useState(false)
  const [capturedImage, setCapturedImage] = useState(null)
  const [cameraError, setCameraError] = useState('')
  const [cameraSuccess, setCameraSuccess] = useState('')
  const [enrollingFace, setEnrollingFace] = useState(false)

  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const previewUrlRef = useRef(null)
  const captureRequestRef = useRef(0)
  const enrollmentRequestRef = useRef(0)
  const mountedRef = useRef(true)

  const releaseCamera = useCallback(() => {
    stopCamera(streamRef.current)
    streamRef.current = null
    setCameraStream(null)

    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
  }, [])

  const releasePreview = useCallback(() => {
    if (previewUrlRef.current) {
      URL.revokeObjectURL(previewUrlRef.current)
      previewUrlRef.current = null
    }
  }, [])

  const closeFaceDialog = useCallback(() => {
    captureRequestRef.current += 1
    enrollmentRequestRef.current += 1
    releaseCamera()
    releasePreview()
    setCameraStudent(null)
    setCapturedImage(null)
    setCameraError('')
    setCameraSuccess('')
    setCameraStarting(false)
    setEnrollingFace(false)
  }, [releaseCamera, releasePreview])

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
          getErrorMessage(
            err,
            'Unable to load students. Check the backend connection.',
          ),
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
        email: newStudent.email ? newStudent.email.trim() || null : null,
      })
      setNewStudent(EMPTY_STUDENT_FORM)
      notifyClassroomDataChanged()
    } catch (err) {
      setActionError(getErrorMessage(err, 'Unable to enroll this student.'))
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
        email: editStudent.email ? editStudent.email.trim() || null : null,
      })
      setEditingStudentId('')
      notifyClassroomDataChanged()
    } catch (err) {
      setActionError(getErrorMessage(err, 'Unable to save student changes.'))
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
        getErrorMessage(err, 'Unable to update classroom enrollment.'),
      )
    } finally {
      setSavingAction(false)
    }
  }

  async function openFaceDialog(student) {
    closeFaceDialog()
    setCameraStudent(student)
    setCameraError('')
    setCameraSuccess('')
    setCameraStarting(true)

    const requestId = ++captureRequestRef.current

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error(
          'Camera access is unavailable. Use localhost or a secure HTTPS connection.',
        )
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'user',
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      })

      if (
        !mountedRef.current ||
        requestId !== captureRequestRef.current
      ) {
        stopCamera(stream)
        return
      }

      streamRef.current = stream
      setCameraStream(stream)
      setCameraStarting(false)
    } catch (err) {
      if (requestId === captureRequestRef.current && mountedRef.current) {
        setCameraError(
          err?.name === 'NotAllowedError'
            ? 'Camera permission was denied. Allow camera access in your browser settings and try again.'
            : getErrorMessage(err, 'Unable to start the camera.'),
        )
        setCameraStarting(false)
      }
    }
  }

  useEffect(() => {
    if (!cameraStream || !videoRef.current) return

    const video = videoRef.current
    video.srcObject = cameraStream
    video.play().catch(() => {
      setCameraError('Unable to start the camera preview. Please try again.')
    })
  }, [cameraStream])

  async function handleCapture() {
    if (!videoRef.current || !cameraStream || cameraStarting) return

    setCameraError('')
    setCameraSuccess('')

    try {
      const blob = await createJpegBlob(videoRef.current)
      releasePreview()
      const previewUrl = URL.createObjectURL(blob)
      previewUrlRef.current = previewUrl
      setCapturedImage({ blob, url: previewUrl })
      releaseCamera()
    } catch (err) {
      setCameraError(getErrorMessage(err, 'Unable to capture the image.'))
    }
  }

  async function handleRetake() {
    releasePreview()
    setCapturedImage(null)
    setCameraError('')
    setCameraSuccess('')
    setCameraStarting(true)

    const requestId = ++captureRequestRef.current

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'user',
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      })

      if (
        !mountedRef.current ||
        requestId !== captureRequestRef.current
      ) {
        stopCamera(stream)
        return
      }

      streamRef.current = stream
      setCameraStream(stream)
      setCameraStarting(false)
    } catch (err) {
      setCameraError(getErrorMessage(err, 'Unable to restart the camera.'))
      setCameraStarting(false)
    }
  }

  async function handleEnrollFace() {
    if (!cameraStudent || !capturedImage || enrollingFace) return

    setEnrollingFace(true)
    setCameraError('')
    setCameraSuccess('')

    const requestId = ++enrollmentRequestRef.current

    try {
      const result = await enrollStudentFace(
        cameraStudent.student_id,
        capturedImage.blob,
      )

      if (
        !mountedRef.current ||
        requestId !== enrollmentRequestRef.current
      ) {
        return
      }

      setStudents((current) =>
        current.map((student) =>
          student.student_id === cameraStudent.student_id
            ? { ...student, face_registered: true }
            : student,
        ),
      )

      setCameraSuccess(
        result?.message || 'Face registered successfully.',
      )
      notifyClassroomDataChanged()
    } catch (err) {
      if (
        mountedRef.current &&
        requestId === enrollmentRequestRef.current
      ) {
        setCameraError(
          getErrorMessage(err, 'Unable to register this face.'),
        )
      }
    } finally {
      if (
        mountedRef.current &&
        requestId === enrollmentRequestRef.current
      ) {
        setEnrollingFace(false)
      }
    }
  }

  useEffect(() => {
    mountedRef.current = true

    let controller
    const reload = () => {
      controller?.abort()
      controller = new AbortController()
      loadStudents(controller.signal)
    }

    reload()
    const unsubscribe = subscribeToClassroomDataChanges(reload)

    return () => {
      mountedRef.current = false
      unsubscribe()
      controller?.abort()
      stopCamera(streamRef.current)
      streamRef.current = null

      if (videoRef.current) videoRef.current.srcObject = null
      if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current)
      previewUrlRef.current = null
    }
  }, [loadStudents])

  const filteredStudents = useMemo(() => {
    const query = search.trim().toLocaleLowerCase()
    if (!query) return students

    return students.filter((student) =>
      [
        student.student_id,
        student.name,
        student.email,
        student.department,
        student.section,
      ]
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
            Manage students and register their faces for attendance monitoring.
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
                type={
                  field === 'year'
                    ? 'number'
                    : field === 'email'
                      ? 'email'
                      : 'text'
                }
                min={field === 'year' ? 1 : undefined}
                max={field === 'year' ? 8 : undefined}
                value={newStudent[field]}
                onChange={(event) =>
                  setNewStudent((current) => ({
                    ...current,
                    [field]: event.target.value,
                  }))
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
        <div
          role="alert"
          className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300"
        >
          {actionError}
        </div>
      )}

      {loading && <p className="text-sm text-slate-400">Loading students…</p>}

      {!loading && error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
          <p>{error}</p>
          <button
            type="button"
            onClick={() => loadStudents()}
            className="mt-3 underline"
          >
            Retry
          </button>
        </div>
      )}

      {!loading && !error && students.length === 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-8 text-center">
          <Users className="mx-auto mb-3 text-slate-500" size={32} />
          <h2 className="font-semibold text-white">No students found</h2>
          <p className="mt-2 text-sm text-slate-400">
            The API returned no student records. Register a student using the form above.
          </p>
        </div>
      )}

      {!loading && !error && students.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-slate-800">
          <div className="border-b border-slate-800 p-4">
            <label htmlFor="student-search" className="sr-only">
              Search students
            </label>
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
            <p className="p-6 text-sm text-slate-400">
              No students match this search.
            </p>
          ) : (
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-900 text-slate-400">
                <tr>
                  <th className="px-5 py-3 font-medium">Student ID</th>
                  <th className="px-5 py-3 font-medium">Name</th>
                  <th className="px-5 py-3 font-medium">Email</th>
                  <th className="px-5 py-3 font-medium">Face status</th>
                  <th className="px-5 py-3 font-medium">Classroom membership</th>
                  <th className="px-5 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredStudents.map((student, index) => (
                  <tr
                    key={`${String(getStudentId(student))}-${index}`}
                    className="border-t border-slate-800 text-slate-200"
                  >
                    <td className="px-5 py-4">{getStudentId(student)}</td>

                    <td className="px-5 py-4">
                      {editingStudentId === student.student_id ? (
                        <input
                          aria-label="Student name"
                          value={editStudent.name}
                          onChange={(event) =>
                            setEditStudent((current) => ({
                              ...current,
                              name: event.target.value,
                            }))
                          }
                          className="rounded border border-slate-700 bg-slate-950 px-2 py-1"
                        />
                      ) : (
                        getStudentName(student)
                      )}
                    </td>

                    <td className="px-5 py-4">
                      {editingStudentId === student.student_id ? (
                        <input
                          aria-label="Student email"
                          type="email"
                          value={editStudent.email}
                          onChange={(event) =>
                            setEditStudent((current) => ({
                              ...current,
                              email: event.target.value,
                            }))
                          }
                          className="rounded border border-slate-700 bg-slate-950 px-2 py-1"
                        />
                      ) : (
                        student.email ?? student.email_address ?? '—'
                      )}
                    </td>

                    <td className="px-5 py-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`rounded-full px-2 py-1 text-xs ${
                            student.face_registered
                              ? 'bg-emerald-500/10 text-emerald-300'
                              : 'bg-amber-500/10 text-amber-300'
                          }`}
                        >
                          {student.face_registered ? 'Registered' : 'Not registered'}
                        </span>

                        <button
                          type="button"
                          onClick={() => openFaceDialog(student)}
                          disabled={enrollingFace || cameraStarting}
                          className="inline-flex items-center gap-1 rounded border border-slate-700 px-2 py-1 text-xs text-slate-200 hover:bg-slate-800 disabled:opacity-50"
                        >
                          <Camera size={13} />
                          {student.face_registered ? 'Update face' : 'Register face'}
                        </button>
                      </div>
                    </td>

                    <td className="px-5 py-4">
                      {student.classroom_is_active === null
                        ? 'Not provided'
                        : student.classroom_is_active
                          ? 'Active'
                          : 'Inactive'}
                    </td>

                    <td className="px-5 py-4">
                      {editingStudentId === student.student_id ? (
                        <form
                          onSubmit={handleSaveStudent}
                          className="flex flex-wrap gap-2"
                        >
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
                              onChange={(event) =>
                                setEditStudent((current) => ({
                                  ...current,
                                  [field]: event.target.value,
                                }))
                              }
                              className="w-24 rounded border border-slate-700 bg-slate-950 px-2 py-1"
                            />
                          ))}
                          <button
                            type="submit"
                            disabled={savingAction}
                            aria-label="Save student"
                            className="rounded p-2 text-emerald-300 hover:bg-slate-800"
                          >
                            <Check size={16} />
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingStudentId('')}
                            aria-label="Cancel edit"
                            className="rounded p-2 text-slate-400 hover:bg-slate-800"
                          >
                            <X size={16} />
                          </button>
                        </form>
                      ) : (
                        <div className="flex flex-wrap items-center gap-2">
                          <button
                            type="button"
                            onClick={() => startEditing(student)}
                            className="inline-flex items-center gap-1 rounded border border-slate-700 px-2 py-1 text-xs text-slate-200 hover:bg-slate-800"
                          >
                            <Pencil size={13} /> Edit
                          </button>
                          <button
                            type="button"
                            disabled={savingAction}
                            onClick={() => handleMembershipChange(student)}
                            className="inline-flex items-center gap-1 rounded border border-slate-700 px-2 py-1 text-xs text-slate-200 hover:bg-slate-800 disabled:opacity-50"
                          >
                            {student.classroom_is_active ? (
                              <>
                                <UserMinus size={13} /> Remove
                              </>
                            ) : (
                              <>
                                <UserPlus size={13} /> Enroll
                              </>
                            )}
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {cameraStudent && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/80 p-4"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !enrollingFace) {
              closeFaceDialog()
            }
          }}
        >
          <section
            role="dialog"
            aria-modal="true"
            aria-labelledby="face-dialog-title"
            className="my-auto w-full max-w-xl rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-2xl"
          >
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-wider text-sky-400">
                  Face registration
                </p>
                <h2 id="face-dialog-title" className="mt-1 text-xl font-semibold text-white">
                  {getStudentName(cameraStudent)}
                </h2>
                <p className="mt-1 text-sm text-slate-400">
                  Student ID: {cameraStudent.student_id}
                </p>
              </div>
              <button
                type="button"
                onClick={closeFaceDialog}
                disabled={enrollingFace}
                aria-label="Close face registration"
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 disabled:opacity-50"
              >
                <X size={20} />
              </button>
            </div>

            <div className="overflow-hidden rounded-xl border border-slate-700 bg-black">
              {capturedImage ? (
                <img
                  src={capturedImage.url}
                  alt={`Captured face of ${getStudentName(cameraStudent)}`}
                  className="max-h-96 w-full object-contain"
                />
              ) : (
                <video
                  ref={videoRef}
                  autoPlay
                  muted
                  playsInline
                  className="max-h-96 w-full object-contain"
                />
              )}
            </div>

            <p className="mt-3 text-xs leading-5 text-slate-400">
              Ask the student for consent before capturing. Use good lighting,
              keep the face centered, remove obstructions, and capture one face
              only. The image is sent to your configured backend for enrollment.
            </p>

            {cameraStarting && (
              <p className="mt-3 text-sm text-slate-300">Starting camera…</p>
            )}

            {cameraError && (
              <p role="alert" className="mt-3 rounded-lg bg-red-500/10 p-3 text-sm text-red-300">
                {cameraError}
              </p>
            )}

            {cameraSuccess && (
              <p role="status" className="mt-3 rounded-lg bg-emerald-500/10 p-3 text-sm text-emerald-300">
                {cameraSuccess}
              </p>
            )}

            <div className="mt-5 flex flex-wrap justify-end gap-2">
              {capturedImage ? (
                <>
                  <button
                    type="button"
                    onClick={handleRetake}
                    disabled={enrollingFace}
                    className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-4 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
                  >
                    <RotateCcw size={16} /> Retake
                  </button>
                  <button
                    type="button"
                    onClick={handleEnrollFace}
                    disabled={enrollingFace}
                    className="inline-flex items-center gap-2 rounded-lg bg-sky-500 px-4 py-2 text-sm font-medium text-white hover:bg-sky-400 disabled:opacity-50"
                  >
                    {enrollingFace ? (
                      <RefreshCw size={16} className="animate-spin" />
                    ) : (
                      <Upload size={16} />
                    )}
                    {enrollingFace ? 'Enrolling…' : 'Enroll face'}
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  onClick={handleCapture}
                  disabled={!cameraStream || cameraStarting}
                  className="inline-flex items-center gap-2 rounded-lg bg-sky-500 px-4 py-2 text-sm font-medium text-white hover:bg-sky-400 disabled:opacity-50"
                >
                  <Camera size={16} /> Capture face
                </button>
              )}

              {cameraSuccess && (
                <button
                  type="button"
                  onClick={closeFaceDialog}
                  className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-white hover:bg-slate-800"
                >
                  Done
                </button>
              )}
            </div>
          </section>
        </div>
      )}
    </main>
  )
}
