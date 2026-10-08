import axios from 'axios'

const monitoringApi = axios.create({
  baseURL: '/monitoring',
  timeout: 5000,
})

export async function getMonitoringState() {
  const response = await monitoringApi.get('/api/state')

  return response.data
}

export async function getMonitoringAlerts() {
  const response = await monitoringApi.get('/api/alerts')

  return response.data
}

export async function acknowledgeMonitoringAlert(alertId) {
  if (!alertId) {
    throw new Error('Alert ID is required.')
  }

  const response = await monitoringApi.get(
    '/api/alerts/acknowledge',
    {
      params: {
        alert_id: alertId,
      },
    },
  )

  return response.data
}

export async function clearMonitoringAlert(alertId) {
  if (!alertId) {
    throw new Error('Alert ID is required.')
  }

  const response = await monitoringApi.get(
    '/api/alerts/clear',
    {
      params: {
        alert_id: alertId,
      },
    },
  )

  return response.data
}

export function getMonitoringVideoUrl() {
  return '/monitoring/video'
}