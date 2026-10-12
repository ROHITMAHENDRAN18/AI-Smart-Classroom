import { useCallback, useEffect, useRef, useState } from 'react'
import {
  AlertCircle,
  Bell,
  CalendarClock,
  RefreshCw,
  ShieldAlert,
  UserRound,
  Wifi,
  WifiOff,
} from 'lucide-react'

import {
  getMonitoringAlerts,
  getMonitoringErrorMessage,
} from '../services/monitoringService'

function formatTimestamp(value) {
  if (!value) {
    return 'Time unavailable'
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return 'Time unavailable'
  }

  return date.toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function formatAlertType(value) {
  return value
    .toLowerCase()
    .split(/[_\s]+/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

export default function Alerts() {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState('')
  const requestSequence = useRef(0)
  const activeRequest = useRef(null)

  const loadAlerts = useCallback(async (initialLoad = false) => {
    activeRequest.current?.abort()

    const controller = new AbortController()
    const requestId = ++requestSequence.current
    activeRequest.current = controller

    setError('')
    if (initialLoad) {
      setLoading(true)
    } else {
      setRefreshing(true)
    }

    try {
      const records = await getMonitoringAlerts({
        limit: 50,
        offset: 0,
        signal: controller.signal,
      })

      if (requestId !== requestSequence.current) {
        return
      }

      setAlerts(records)
      setConnected(true)
    } catch (requestError) {
      if (
        controller.signal.aborted ||
        requestId !== requestSequence.current
      ) {
        return
      }

      setAlerts([])
      setConnected(false)
      setError(getMonitoringErrorMessage(requestError))
    } finally {
      if (requestId === requestSequence.current) {
        setLoading(false)
        setRefreshing(false)
      }
    }
  }, [])

  useEffect(() => {
    loadAlerts(true)

    return () => {
      requestSequence.current += 1
      activeRequest.current?.abort()
    }
  }, [loadAlerts])

  const isBusy = loading || refreshing

  return (
    <div className="min-h-screen bg-[#070b16] px-4 py-6 text-white sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-2">
              <span className="text-sm font-medium text-blue-400">
                Classroom operations
              </span>
              <span
                className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${
                  connected
                    ? 'border-emerald-400/20 bg-emerald-400/10 text-emerald-300'
                    : 'border-slate-400/20 bg-slate-400/10 text-slate-300'
                }`}
              >
                {connected ? <Wifi size={12} /> : <WifiOff size={12} />}
                {connected ? 'Alert service available' : 'Not connected'}
              </span>
            </div>

            <h1 className="text-3xl font-bold tracking-tight">Alerts</h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-400">
              Attention alerts are derived from persisted NOT ATTENTIVE
              records in your classroom sessions.
            </p>
          </div>

          <button
            type="button"
            onClick={() => loadAlerts(false)}
            disabled={isBusy}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <RefreshCw
              size={16}
              className={refreshing ? 'animate-spin' : ''}
            />
            Refresh
          </button>
        </header>

        <div className="mb-6 rounded-xl border border-blue-400/15 bg-blue-500/5 px-4 py-3 text-sm text-slate-300">
          Severity is not stored with attention records and is therefore not
          shown. Alert history is read-only.
        </div>

        {error && (
          <div
            role="alert"
            className="mb-6 flex flex-col gap-3 rounded-xl border border-red-400/20 bg-red-500/10 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
          >
            <div className="flex items-start gap-3 text-sm text-red-300">
              <AlertCircle size={18} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              type="button"
              onClick={() => loadAlerts(false)}
              disabled={isBusy}
              className="inline-flex w-fit items-center gap-2 rounded-lg border border-red-400/20 px-3 py-2 text-xs font-semibold text-red-200 transition hover:bg-red-500/10 disabled:opacity-50"
            >
              <RefreshCw
                size={14}
                className={refreshing ? 'animate-spin' : ''}
              />
              Retry
            </button>
          </div>
        )}

        <section className="overflow-hidden rounded-2xl border border-white/10 bg-[#0b1220]">
          <div className="flex flex-col gap-2 border-b border-white/10 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="flex items-center gap-2">
                <ShieldAlert size={18} className="text-amber-400" />
                <h2 className="font-semibold">Attention alerts</h2>
              </div>
              <p className="mt-1 text-xs text-slate-500">
                Latest persisted events, up to 50 records.
              </p>
            </div>
            {!loading && !error && (
              <span className="w-fit rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300">
                {alerts.length} {alerts.length === 1 ? 'record' : 'records'}
              </span>
            )}
          </div>

          {loading ? (
            <div
              role="status"
              className="flex items-center justify-center px-5 py-12 text-sm text-slate-400"
            >
              <RefreshCw size={16} className="mr-2 animate-spin" />
              Loading alerts...
            </div>
          ) : error ? null : alerts.length === 0 ? (
            <div className="px-5 py-12 text-center">
              <Bell size={26} className="mx-auto mb-3 text-slate-500" />
              <h3 className="font-semibold text-white">No alerts found</h3>
              <p className="mt-2 text-sm text-slate-400">
                No NOT ATTENTIVE records were returned for your classroom
                sessions.
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-white/5">
              {alerts.map((alert) => (
                <li key={alert.alert_id} className="px-5 py-5">
                  <article className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full border border-amber-400/20 bg-amber-400/10 px-2.5 py-1 text-xs font-semibold text-amber-300">
                          {formatAlertType(alert.alert_type)}
                        </span>
                        {alert.severity && (
                          <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-slate-300">
                            {formatAlertType(alert.severity)}
                          </span>
                        )}
                        <span className="text-xs text-slate-500">
                          {formatTimestamp(alert.timestamp)}
                        </span>
                      </div>

                      <p className="mt-3 text-sm leading-6 text-slate-200">
                        {alert.message}
                      </p>

                      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-xs text-slate-400">
                        <span className="inline-flex items-center gap-1.5">
                          <UserRound size={14} className="text-slate-500" />
                          Student {alert.student_id}
                        </span>
                        {alert.track_id !== null && (
                          <span>Track #{alert.track_id}</span>
                        )}
                        <span className="inline-flex items-center gap-1.5">
                          <CalendarClock size={14} className="text-slate-500" />
                          Session {alert.session_id}
                        </span>
                      </div>
                    </div>
                  </article>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  )
}
