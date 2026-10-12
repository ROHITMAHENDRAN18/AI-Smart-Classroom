/**
 * Format duration in seconds to HH:MM:SS.
 * Examples:
 *   0 -> 00:00:00
 *   65 -> 00:01:05
 *   3661 -> 01:01:01
 */
export function formatDuration(seconds) {
  if (seconds === null || seconds === undefined || seconds === '') {
    return '—'
  }

  const total = Number(seconds)

  if (!Number.isFinite(total) || total < 0) {
    return '—'
  }

  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const remainingSeconds = Math.floor(total % 60)

  const pad = (n) => String(n).padStart(2, '0')

  return `${pad(hours)}:${pad(minutes)}:${pad(remainingSeconds)}`
}

/**
 * Format ISO datetime string or Date object to a readable date/time string.
 */
export function formatDateTime(value) {
  if (!value) {
    return '—'
  }

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return '—'
  }

  return date.toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

/**
 * Format a number as a percentage string.
 */
export function formatPercentage(value, decimals = 1) {
  if (value === null || value === undefined || value === '') {
    return '0%'
  }

  const num = Number(value)
  if (!Number.isFinite(num)) {
    return '0%'
  }

  return `${num.toFixed(decimals)}%`
}

/**
 * Format a confidence score (typically 0.0 - 1.0) as percentage.
 */
export function formatConfidence(value) {
  if (value === null || value === undefined || value === '') {
    return '—'
  }

  const num = Number(value)
  if (!Number.isFinite(num)) {
    return '—'
  }

  const pct = num <= 1.0 ? num * 100 : num
  return `${pct.toFixed(1)}%`
}
