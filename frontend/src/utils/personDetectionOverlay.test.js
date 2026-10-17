import assert from 'node:assert/strict'
import test from 'node:test'

import {
  EMPTY_DETECTION_OVERLAY,
  expirePersonDetectionOverlay,
  getNextPersonDetectionExpiry,
  toVideoCoordinates,
  updatePersonDetectionOverlay,
} from './personDetectionOverlay.js'

const GRACE_PERIOD_MS = 6000

function result(detections, frameWidth = 640, frameHeight = 480) {
  return { detections, frame_width: frameWidth, frame_height: frameHeight }
}

function person(x1, y1, x2, y2, confidence = 0.8) {
  return {
    class_label: 'person',
    x1,
    y1,
    x2,
    y2,
    confidence,
  }
}

test('a missed detection retains the last real box only for the grace period', () => {
  const detected = updatePersonDetectionOverlay(
    EMPTY_DETECTION_OVERLAY,
    result([person(64, 48, 192, 240)]),
    1,
    1000,
    GRACE_PERIOD_MS,
  )
  const missed = updatePersonDetectionOverlay(
    detected,
    result([]),
    2,
    3000,
    GRACE_PERIOD_MS,
  )

  assert.equal(missed.boxes.length, 1)
  assert.equal(missed.boxes[0].lastSeenAt, 1000)
  assert.equal(
    expirePersonDetectionOverlay(missed, 6999, GRACE_PERIOD_MS).boxes.length,
    1,
  )
  assert.equal(
    expirePersonDetectionOverlay(missed, 7000, GRACE_PERIOD_MS).boxes.length,
    0,
  )
})

test('a missed person is retained while another person remains detected', () => {
  const detected = updatePersonDetectionOverlay(
    EMPTY_DETECTION_OVERLAY,
    result([
      person(64, 48, 192, 240),
      person(384, 48, 512, 240),
    ]),
    1,
    1000,
    GRACE_PERIOD_MS,
  )
  const partial = updatePersonDetectionOverlay(
    detected,
    result([person(384, 48, 512, 240)]),
    2,
    2000,
    GRACE_PERIOD_MS,
  )

  assert.equal(partial.boxes.length, 2)
  assert.deepEqual(
    partial.boxes.map((box) => box.lastSeenAt),
    [2000, 1000],
  )
})

test('a later real detection refreshes the box and smooths small movement', () => {
  const detected = updatePersonDetectionOverlay(
    EMPTY_DETECTION_OVERLAY,
    result([person(64, 48, 192, 240)]),
    1,
    1000,
    GRACE_PERIOD_MS,
  )
  const moved = updatePersonDetectionOverlay(
    detected,
    result([person(96, 48, 224, 240)]),
    2,
    2500,
    GRACE_PERIOD_MS,
  )

  assert.equal(moved.boxes.length, 1)
  assert.equal(moved.boxes[0].lastSeenAt, 2500)
  assert.ok(moved.boxes[0].x1 > 64 / 640)
  assert.ok(moved.boxes[0].x1 < 96 / 640)
})

test('older out-of-order inference results cannot replace newer boxes', () => {
  const newer = updatePersonDetectionOverlay(
    EMPTY_DETECTION_OVERLAY,
    result([person(320, 48, 448, 240)]),
    2,
    2000,
    GRACE_PERIOD_MS,
  )
  const stale = updatePersonDetectionOverlay(
    newer,
    result([person(32, 48, 160, 240)]),
    1,
    1500,
    GRACE_PERIOD_MS,
  )

  assert.equal(stale, newer)
  assert.ok(stale.boxes[0].x1 > 0.4)
})

test('normalized boxes map correctly when the live video dimensions differ', () => {
  const overlay = updatePersonDetectionOverlay(
    EMPTY_DETECTION_OVERLAY,
    result([person(64, 48, 192, 240)], 640, 480),
    1,
    1000,
    GRACE_PERIOD_MS,
  )
  const box = toVideoCoordinates(overlay.boxes[0], 1280, 720)

  assert.deepEqual(
    [box.x1, box.y1, box.x2, box.y2],
    [128, 72, 384, 360],
  )
})

test('the expiry scheduler reports the nearest box deadline and stops when empty', () => {
  const overlay = updatePersonDetectionOverlay(
    EMPTY_DETECTION_OVERLAY,
    result([person(64, 48, 192, 240)]),
    1,
    1000,
    GRACE_PERIOD_MS,
  )

  assert.equal(getNextPersonDetectionExpiry(overlay, 2500, GRACE_PERIOD_MS), 4500)
  assert.equal(
    getNextPersonDetectionExpiry(
      expirePersonDetectionOverlay(overlay, 7000, GRACE_PERIOD_MS),
      7000,
      GRACE_PERIOD_MS,
    ),
    null,
  )
})

test('track IDs are preserved when the same person is detected again', () => {
  const first = updatePersonDetectionOverlay(
    EMPTY_DETECTION_OVERLAY,
    result([{ ...person(64, 48, 192, 240), track_id: 7 }]),
    1,
    1000,
    GRACE_PERIOD_MS,
  )

  const second = updatePersonDetectionOverlay(
    first,
    result([{ ...person(200, 80, 320, 300), track_id: 7 }]),
    2,
    1600,
    GRACE_PERIOD_MS,
  )

  assert.equal(second.boxes.length, 1)
  assert.equal(second.boxes[0].trackId, 7)
  assert.ok(second.boxes[0].x1 > 0.1)
})

test('invalid input is treated as an empty overlay without crashing', () => {
  const overlay = updatePersonDetectionOverlay(
    undefined,
    { detections: undefined, frame_width: 0, frame_height: 0 },
    1,
    1000,
    GRACE_PERIOD_MS,
  )

  assert.deepEqual(overlay, { sequence: 1, boxes: [] })
  assert.equal(getNextPersonDetectionExpiry(undefined, 1000, GRACE_PERIOD_MS), null)
  assert.equal(toVideoCoordinates(null, 1280, 720), null)
})
