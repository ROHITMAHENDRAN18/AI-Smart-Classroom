import assert from 'node:assert/strict'
import test from 'node:test'

import { parseClassroomId } from './classroomConfig.js'

test('parses a positive integer classroom ID', () => {
  assert.deepEqual(parseClassroomId('2'), {
    classroomId: 2,
    error: '',
  })
})

test('reports a missing classroom ID with actionable configuration guidance', () => {
  const result = parseClassroomId('  ')

  assert.equal(result.classroomId, null)
  assert.match(result.error, /VITE_DEFAULT_CLASSROOM_ID is missing/)
  assert.match(result.error, /frontend\/\.env/)
  assert.match(result.error, /restart Vite/)
})

test('rejects invalid, non-positive, and unsafe classroom IDs', () => {
  for (const value of ['abc', '1.5', '0', '-2', '9007199254740992']) {
    const result = parseClassroomId(value)
    assert.equal(result.classroomId, null, `unexpected ID for ${value}`)
    assert.match(result.error, /must be a positive integer/)
  }
})
