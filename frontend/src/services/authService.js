import axios from 'axios'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  'http://127.0.0.1:8000/api/v1'

const authApi = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export async function login(username, password) {
  const response = await authApi.post('/auth/login', {
    username,
    password,
  })

  return response.data
}

export async function getCurrentUser(token) {
  const response = await authApi.get('/auth/me', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  return response.data
}

export function saveAuthSession(data) {
  localStorage.setItem('access_token', data.access_token)

  if (data.user) {
    localStorage.setItem('auth_user', JSON.stringify(data.user))
  }
}

export function getAccessToken() {
  return localStorage.getItem('access_token')
}

export function getStoredUser() {
  const user = localStorage.getItem('auth_user')

  if (!user) {
    return null
  }

  try {
    return JSON.parse(user)
  } catch {
    return null
  }
}

export function clearAuthSession() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('auth_user')
}
