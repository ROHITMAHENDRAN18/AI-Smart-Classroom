import assert from 'node:assert/strict'
import test from 'node:test'

import {
  notifyClassroomDataChanged,
  subscribeToClassroomDataChanges,
} from './classroomDataEvents.js'

test('classroom data subscriptions are removed during cleanup', () => {
  const previousWindow = globalThis.window
  globalThis.window = new EventTarget()
  let changes = 0
  const unsubscribe = subscribeToClassroomDataChanges(() => {
    changes += 1
  })

  try {
    notifyClassroomDataChanged()
    assert.equal(changes, 1)
    unsubscribe()
    notifyClassroomDataChanged()
    assert.equal(changes, 1)
  } finally {
    if (previousWindow === undefined) {
      delete globalThis.window
    } else {
      globalThis.window = previousWindow
    }
  }
})
