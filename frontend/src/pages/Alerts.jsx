import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  Bell,
  Check,
  CheckCircle2,
  Clock3,
  Eraser,
  RefreshCw,
  ShieldAlert,
  User,
  Wifi,
  WifiOff,
} from 'lucide-react'

import {
  acknowledgeMonitoringAlert,
  clearMonitoringAlert,
  getMonitoringAlerts,
} from '../services/monitoringService'

const REFRESH_INTERVAL = 2000

const ALERT_STATUS = {
  ACTIVE: 'ACTIVE',
  ACKNOWLEDGED: 'ACKNOWLEDGED',
  CLEARED: 'CLEARED',
}

function normalizeAlerts(data) {
  if (Array.isArray(data)) {
    return data
  }

  if (Array.isArray(data?.alerts)) {
    return data.alerts
  }

  if (Array.isArray(data?.items)) {
    return data.items
  }

  return []
}

function normalizeStatistics(data, alerts) {
  const statistics = data?.statistics || {}

  return {
    total: Number(statistics.total ?? alerts.length),
    active: Number(
      statistics.active ??
        alerts.filter(
          (alert) =>
            String(alert.status).toUpperCase() ===
            ALERT_STATUS.ACTIVE,
        ).length,
    ),
    acknowledged: Number(
      statistics.acknowledged ??
        alerts.filter(
          (alert) =>
            String(alert.status).toUpperCase() ===
            ALERT_STATUS.ACKNOWLEDGED,
        ).length,
    ),
    cleared: Number(
      statistics.cleared ??
        alerts.filter(
          (alert) =>
            String(alert.status).toUpperCase() ===
            ALERT_STATUS.CLEARED,
        ).length,
    ),
  }
}

function normalizeStatus(status) {
  return String(status || 'UNKNOWN').toUpperCase()
}

function formatTimestamp(value) {
  if (!value) {
    return '—'
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return String(value)
  }

  return date.toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function getStatusClasses(status) {
  if (status === ALERT_STATUS.ACTIVE) {
    return 'border-red-400/20 bg-red-500/10 text-red-300'
  }

  if (status === ALERT_STATUS.ACKNOWLEDGED) {
    return 'border-amber-400/20 bg-amber-500/10 text-amber-300'
  }

  if (status === ALERT_STATUS.CLEARED) {
    return 'border-emerald-400/20 bg-emerald-500/10 text-emerald-300'
  }

  return 'border-white/10 bg-white/5 text-slate-400'
}

function getStatusIcon(status) {
  if (status === ALERT_STATUS.ACTIVE) {
    return <AlertCircle size={13} />
  }

  if (status === ALERT_STATUS.ACKNOWLEDGED) {
    return <Check size={13} />
  }

  if (status === ALERT_STATUS.CLEARED) {
    return <CheckCircle2 size={13} />
  }

  return <Clock3 size={13} />
}

function getAlertTitle(alert) {
  return (
    alert.alert_type ||
    alert.type ||
    alert.title ||
    'Classroom Alert'
  )
}

function getAlertMessage(alert) {
  return (
    alert.message ||
    alert.description ||
    'Attention event detected by the classroom monitoring system.'
  )
}

function getAlertStudent(alert) {
  return (
    alert.student_id ||
    alert.studentId ||
    alert.student_name ||
    alert.studentName ||
    null
  )
}

function getAlertTrack(alert) {
  return (
    alert.track_id ??
    alert.trackId ??
    null
  )
}

export default function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [statistics, setStatistics] = useState({
    total: 0,
    active: 0,
    acknowledged: 0,
    cleared: 0,
  })

  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [connected, setConnected] = useState(false)

  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [success, setSuccess] = useState('')

  const [actionLoading, setActionLoading] = useState('')

  const loadAlerts = useCallback(
    async (showSpinner = false) => {
      if (showSpinner) {
        setRefreshing(true)
      }

      try {
        const data = await getMonitoringAlerts()

        const normalizedAlerts = normalizeAlerts(data)

        setAlerts(normalizedAlerts)

        setStatistics(
          normalizeStatistics(
            data,
            normalizedAlerts,
          ),
        )

        setConnected(true)
        setError('')
      } catch (requestError) {
        console.error(
          'Failed to load classroom alerts:',
          requestError,
        )

        setConnected(false)

        setError(
          requestError?.response?.data?.detail ||
            requestError?.message ||
            'Unable to connect to the alert service.',
        )
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    [],
  )

  useEffect(() => {
    loadAlerts()

    const interval = window.setInterval(() => {
      loadAlerts()
    }, REFRESH_INTERVAL)

    return () => {
      window.clearInterval(interval)
    }
  }, [loadAlerts])

  const activeAlerts = useMemo(
    () =>
      alerts.filter(
        (alert) =>
          normalizeStatus(alert.status) ===
          ALERT_STATUS.ACTIVE,
      ),
    [alerts],
  )

  const acknowledgedAlerts = useMemo(
    () =>
      alerts.filter(
        (alert) =>
          normalizeStatus(alert.status) ===
          ALERT_STATUS.ACKNOWLEDGED,
      ),
    [alerts],
  )

  const clearedAlerts = useMemo(
    () =>
      alerts.filter(
        (alert) =>
          normalizeStatus(alert.status) ===
          ALERT_STATUS.CLEARED,
      ),
    [alerts],
  )

  const handleAcknowledge = async (alert) => {
    const alertId = alert?.alert_id

    if (!alertId) {
      setActionError('Alert ID is missing.')
      return
    }

    setActionLoading(`ack:${alertId}`)
    setActionError('')
    setSuccess('')

    try {
      const result =
        await acknowledgeMonitoringAlert(alertId)

      if (result?.success === false) {
        throw new Error(
          'The alert could not be acknowledged.',
        )
      }

      setSuccess(
        `Alert ${alertId} acknowledged successfully.`,
      )

      await loadAlerts()
    } catch (requestError) {
      console.error(
        'Failed to acknowledge alert:',
        requestError,
      )

      setActionError(
        requestError?.response?.data?.detail ||
          requestError?.message ||
          'Unable to acknowledge alert.',
      )
    } finally {
      setActionLoading('')
    }
  }

  const handleClear = async (alert) => {
    const alertId = alert?.alert_id

    if (!alertId) {
      setActionError('Alert ID is missing.')
      return
    }

    const confirmed = window.confirm(
      `Clear alert ${alertId}?`,
    )

    if (!confirmed) {
      return
    }

    setActionLoading(`clear:${alertId}`)
    setActionError('')
    setSuccess('')

    try {
      const result =
        await clearMonitoringAlert(alertId)

      if (result?.success === false) {
        throw new Error(
          'The alert could not be cleared.',
        )
      }

      setSuccess(
        `Alert ${alertId} cleared successfully.`,
      )

      await loadAlerts()
    } catch (requestError) {
      console.error(
        'Failed to clear alert:',
        requestError,
      )

      setActionError(
        requestError?.response?.data?.detail ||
          requestError?.message ||
          'Unable to clear alert.',
      )
    } finally {
      setActionLoading('')
    }
  }

  const handleRefresh = async () => {
    setSuccess('')
    setActionError('')

    await loadAlerts(true)
  }

  return (
    <div className="min-h-screen bg-[#070b16] px-4 py-6 text-white sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">

        {/* Header */}
        <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-2">
              <span className="text-sm font-medium text-blue-400">
                Classroom operations
              </span>

              <span
                className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${
                  connected
                    ? 'border-emerald-400/20 bg-emerald-400/10 text-emerald-300'
                    : 'border-red-400/20 bg-red-400/10 text-red-300'
                }`}
              >
                {connected ? (
                  <>
                    <Wifi size={12} />
                    Alert service connected
                  </>
                ) : (
                  <>
                    <WifiOff size={12} />
                    Alert service disconnected
                  </>
                )}
              </span>
            </div>

            <h1 className="text-3xl font-bold tracking-tight">
              Alerts
            </h1>

            <p className="mt-2 max-w-2xl text-sm text-slate-400">
              Monitor classroom attention alerts and manage
              their acknowledgement state.
            </p>
          </div>

          <button
            type="button"
            onClick={handleRefresh}
            disabled={loading || refreshing}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCw
              size={16}
              className={
                refreshing ? 'animate-spin' : ''
              }
            />

            Refresh
          </button>
        </div>

        {/* Errors */}
        {error && (
          <div className="mb-5 flex items-start gap-3 rounded-xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            <AlertCircle
              size={18}
              className="mt-0.5 shrink-0"
            />

            <span>{error}</span>
          </div>
        )}

        {actionError && (
          <div className="mb-5 flex items-start gap-3 rounded-xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            <AlertCircle
              size={18}
              className="mt-0.5 shrink-0"
            />

            <span>{actionError}</span>
          </div>
        )}

        {success && (
          <div className="mb-5 flex items-start gap-3 rounded-xl border border-emerald-400/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
            <CheckCircle2
              size={18}
              className="mt-0.5 shrink-0"
            />

            <span>{success}</span>
          </div>
        )}

        {/* Statistics */}
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            icon={<Bell size={18} />}
            label="Total Alerts"
            value={statistics.total}
            description="All recorded alerts"
          />

          <StatCard
            icon={<ShieldAlert size={18} />}
            label="Active"
            value={statistics.active}
            description="Require attention"
          />

          <StatCard
            icon={<Check size={18} />}
            label="Acknowledged"
            value={statistics.acknowledged}
            description="Reviewed by teacher"
          />

          <StatCard
            icon={<CheckCircle2 size={18} />}
            label="Cleared"
            value={statistics.cleared}
            description="Resolved alerts"
          />
        </div>

        {/* Active Alerts */}
        <section className="mb-6 overflow-hidden rounded-2xl border border-white/10 bg-[#0b1220]">
          <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
            <div>
              <div className="flex items-center gap-2">
                <ShieldAlert
                  size={18}
                  className="text-red-400"
                />

                <h2 className="font-semibold">
                  Active Alerts
                </h2>
              </div>

              <p className="mt-1 text-xs text-slate-500">
                Alerts currently requiring teacher attention.
              </p>
            </div>

            <span className="rounded-lg border border-red-400/20 bg-red-500/10 px-3 py-1.5 text-xs text-red-300">
              {activeAlerts.length} active
            </span>
          </div>

          {loading ? (
            <div className="flex items-center justify-center px-5 py-12 text-sm text-slate-400">
              <RefreshCw
                size={16}
                className="mr-2 animate-spin"
              />

              Loading alerts...
            </div>
          ) : activeAlerts.length === 0 ? (
            <EmptyState
              icon={<CheckCircle2 size={24} />}
              title="No active alerts"
              description="The classroom monitoring system has no active alerts right now."
            />
          ) : (
            <div className="divide-y divide-white/5">
              {activeAlerts.map((alert) => (
                <AlertRow
                  key={alert.alert_id}
                  alert={alert}
                  actionLoading={actionLoading}
                  onAcknowledge={handleAcknowledge}
                  onClear={handleClear}
                />
              ))}
            </div>
          )}
        </section>

        {/* Alert History */}
        <section className="overflow-hidden rounded-2xl border border-white/10 bg-[#0b1220]">
          <div className="border-b border-white/10 px-5 py-4">
            <div className="flex items-center gap-2">
              <Clock3
                size={18}
                className="text-blue-400"
              />

              <h2 className="font-semibold">
                Alert History
              </h2>
            </div>

            <p className="mt-1 text-xs text-slate-500">
              Recent acknowledged and cleared alerts.
            </p>
          </div>

          {acknowledgedAlerts.length === 0 &&
          clearedAlerts.length === 0 ? (
            <EmptyState
              icon={<Clock3 size={24} />}
              title="No alert history"
              description="Acknowledged and cleared alerts will appear here."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[800px]">
                <thead>
                  <tr className="border-b border-white/10 text-left text-[11px] uppercase tracking-wider text-slate-500">
                    <th className="px-5 py-4 font-medium">
                      Alert
                    </th>

                    <th className="px-5 py-4 font-medium">
                      Status
                    </th>

                    <th className="px-5 py-4 font-medium">
                      Student / Track
                    </th>

                    <th className="px-5 py-4 font-medium">
                      Timestamp
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {[
                    ...acknowledgedAlerts,
                    ...clearedAlerts,
                  ].map((alert) => {
                    const status = normalizeStatus(
                      alert.status,
                    )

                    const student =
                      getAlertStudent(alert)

                    const track =
                      getAlertTrack(alert)

                    return (
                      <tr
                        key={alert.alert_id}
                        className="border-b border-white/5 last:border-0"
                      >
                        <td className="px-5 py-4">
                          <div className="font-medium text-slate-200">
                            {getAlertTitle(alert)}
                          </div>

                          <div className="mt-1 max-w-xl text-xs text-slate-500">
                            {getAlertMessage(alert)}
                          </div>
                        </td>

                        <td className="px-5 py-4">
                          <StatusBadge
                            status={status}
                          />
                        </td>

                        <td className="px-5 py-4 text-sm text-slate-400">
                          {student || 'Unknown'}
                          {track !== null &&
                            track !== undefined && (
                              <span className="ml-2 text-xs text-slate-600">
                                Track #{track}
                              </span>
                            )}
                        </td>

                        <td className="px-5 py-4 text-sm text-slate-400">
                          {formatTimestamp(
                            alert.timestamp,
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

function AlertRow({
  alert,
  actionLoading,
  onAcknowledge,
  onClear,
}) {
  const alertId = alert.alert_id

  const student = getAlertStudent(alert)
  const track = getAlertTrack(alert)

  return (
    <div className="flex flex-col gap-5 px-5 py-5 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex min-w-0 gap-4">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-red-500/10 text-red-400">
          <AlertCircle size={21} />
        </div>

        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-semibold text-slate-100">
              {getAlertTitle(alert)}
            </h3>

            <StatusBadge status={ALERT_STATUS.ACTIVE} />
          </div>

          <p className="mt-2 text-sm leading-6 text-slate-400">
            {getAlertMessage(alert)}
          </p>

          <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-xs text-slate-600">
            <span>
              Time: {formatTimestamp(alert.timestamp)}
            </span>

            {student && (
              <span className="inline-flex items-center gap-1">
                <User size={12} />
                {student}
              </span>
            )}

            {track !== null &&
              track !== undefined && (
                <span>
                  Track #{track}
                </span>
              )}
          </div>
        </div>
      </div>

      <div className="flex shrink-0 gap-2">
        <button
          type="button"
          onClick={() => onAcknowledge(alert)}
          disabled={
            Boolean(actionLoading)
          }
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-amber-400/20 bg-amber-500/10 px-4 py-2.5 text-sm font-medium text-amber-300 transition hover:bg-amber-500/20 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Check size={15} />

          {actionLoading === `ack:${alertId}`
            ? 'Acknowledging...'
            : 'Acknowledge'}
        </button>

        <button
          type="button"
          onClick={() => onClear(alert)}
          disabled={
            Boolean(actionLoading)
          }
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-red-400/20 bg-red-500/10 px-4 py-2.5 text-sm font-medium text-red-300 transition hover:bg-red-500/20 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Eraser size={15} />

          {actionLoading === `clear:${alertId}`
            ? 'Clearing...'
            : 'Clear'}
        </button>
      </div>
    </div>
  )
}

function StatusBadge({ status }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${getStatusClasses(
        status,
      )}`}
    >
      {getStatusIcon(status)}
      {status}
    </span>
  )
}

function StatCard({
  icon,
  label,
  value,
  description,
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-[#0b1220] p-5">
      <div className="mb-4 flex h-9 w-9 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
        {icon}
      </div>

      <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
        {label}
      </p>

      <p className="mt-1 text-2xl font-semibold text-slate-100">
        {value}
      </p>

      <p className="mt-1 text-xs text-slate-600">
        {description}
      </p>
    </div>
  )
}

function EmptyState({
  icon,
  title,
  description,
}) {
  return (
    <div className="px-5 py-12 text-center">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-white/5 text-slate-500">
        {icon}
      </div>

      <p className="mt-3 font-medium text-slate-300">
        {title}
      </p>

      <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">
        {description}
      </p>
    </div>
  )
}