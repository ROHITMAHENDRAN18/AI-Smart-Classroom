const CLASSROOM_ID_SETTING = 'VITE_DEFAULT_CLASSROOM_ID'

export function parseClassroomId(value) {
  const normalized =
    typeof value === 'string' ? value.trim() : String(value ?? '').trim()

  if (!normalized) {
    return {
      classroomId: null,
      error: `${CLASSROOM_ID_SETTING} is missing. Add ${CLASSROOM_ID_SETTING}=<authorized classroom ID> to frontend/.env and restart Vite.`,
    }
  }

  if (!/^\d+$/.test(normalized)) {
    return {
      classroomId: null,
      error: `${CLASSROOM_ID_SETTING} must be a positive integer classroom ID. Set it in frontend/.env and restart Vite.`,
    }
  }

  const classroomId = Number(normalized)
  if (!Number.isSafeInteger(classroomId) || classroomId < 1) {
    return {
      classroomId: null,
      error: `${CLASSROOM_ID_SETTING} must be a positive integer classroom ID. Set it in frontend/.env and restart Vite.`,
    }
  }

  return { classroomId, error: '' }
}

export function requireClassroomId(value) {
  const { classroomId, error } = parseClassroomId(value)
  if (error) {
    throw new Error(error)
  }
  return classroomId
}
