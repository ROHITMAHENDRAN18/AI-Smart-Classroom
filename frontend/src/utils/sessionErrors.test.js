import assert from 'node:assert/strict'
import test from 'node:test'

import {
  getSessionErrorMessage,
  isNoActiveSessionError,
} from './sessionErrors.js'

test('only the explicit no-active-session 404 is treated as normal absence', () => {
  assert.equal(
    isNoActiveSessionError({
      response: {
        status: 404,
        data: { detail: 'No active classroom session' },
      },
    }),
    true,
  )
  assert.equal(
    isNoActiveSessionError({
      response: { status: 404, data: { detail: 'Not Found' } },
    }),
    false,
  )
})

test('a missing route has a distinct actionable message', () => {
  const message = getSessionErrorMessage({
    response: { status: 404, data: { detail: 'Not Found' } },
  })

  assert.match(message, /expected classroom session route/)
  assert.match(message, /API base URL/)
})

test('missing or unauthorized classrooms are not reported as empty sessions', () => {
  const message = getSessionErrorMessage({
    response: { status: 404, data: { detail: 'Classroom not found' } },
  })

  assert.match(message, /not found or is not accessible/)
})
