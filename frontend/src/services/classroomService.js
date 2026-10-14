import api from './api'
import { getConfiguredClassroomId } from './sessionControlService'
import { requireClassroomId } from '../utils/classroomConfig'

export async function getClassroomOverview(
  classroomId,
  { signal } = {},
) {
  const id =
    classroomId === undefined
      ? getConfiguredClassroomId()
      : requireClassroomId(classroomId)

  try {
    const response = await api.get(`/classrooms/${id}/overview`, { signal })
    return response.data
  } catch (error) {
    if (error?.code === 'ERR_CANCELED') {
      throw error
    }

    if (!error?.response) {
      if (error?.isAxiosError) {
        throw new Error(
          'Cannot reach the classroom service. Check that the FastAPI backend is running, then retry.',
          { cause: error },
        )
      }
      throw error
    }

    const { status } = error.response
    const detail = error.response.data?.detail

    if (status === 401) {
      throw new Error('Your session has expired. Please log in again.', {
        cause: error,
      })
    }
    if (status === 403) {
      throw new Error(
        'Your account is not authorized to view classroom overview.',
        { cause: error },
      )
    }
    if (status === 404 && detail === 'Not Found') {
      throw new Error(
        'The backend does not have the expected classroom overview route. Verify the backend version and API base URL, then restart the backend.',
        { cause: error },
      )
    }
    if (status === 404 && detail === 'Classroom not found') {
      throw new Error(
        `Classroom ${id} was not found or is not accessible to your account. Verify the classroom ID and your classroom access.`,
        { cause: error },
      )
    }
    if (status === 422) {
      throw new Error(
        'The classroom request was invalid. Verify the classroom ID and retry.',
        { cause: error },
      )
    }
    if (status >= 500) {
      throw new Error(
        'The classroom service encountered a server error. Please retry shortly.',
        { cause: error },
      )
    }

    throw new Error(
      `The classroom request failed (HTTP ${status}). Please retry.`,
      { cause: error },
    )
  }
}
