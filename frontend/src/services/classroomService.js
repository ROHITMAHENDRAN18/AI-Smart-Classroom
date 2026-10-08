import api from './api'

export async function getClassroomOverview(classroomId) {
  if (!classroomId) {
    throw new Error('Classroom ID is required')
  }

  const response = await api.get(
    `/classrooms/${classroomId}/overview`,
  )

  return response.data
}
