import api from './api'
import { CLASSROOM_ID } from './sessionControlService'

export async function getClassroomOverview(
  classroomId = CLASSROOM_ID,
  { signal } = {},
) {
  if (!Number.isSafeInteger(classroomId) || classroomId < 1) {
    throw new Error('Set VITE_DEFAULT_CLASSROOM_ID to a valid classroom ID.')
  }

  const response = await api.get(
    `/classrooms/${classroomId}/overview`,
    { signal },
  )

  return response.data
}
