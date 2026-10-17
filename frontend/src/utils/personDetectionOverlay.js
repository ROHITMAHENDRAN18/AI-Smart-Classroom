const MAX_MATCH_DISTANCE = 0.25
const PREVIOUS_BOX_WEIGHT = 0.35

export const EMPTY_DETECTION_OVERLAY = {
  sequence: 0,
  boxes: [],
}

function normalizedDetection(detection, frameWidth, frameHeight, seenAt) {
  const safeFrameWidth = Number.isFinite(frameWidth) && frameWidth > 0 ? frameWidth : 1
  const safeFrameHeight = Number.isFinite(frameHeight) && frameHeight > 0 ? frameHeight : 1

  return {
    x1: detection.x1 / safeFrameWidth,
    y1: detection.y1 / safeFrameHeight,
    x2: detection.x2 / safeFrameWidth,
    y2: detection.y2 / safeFrameHeight,
    confidence: detection.confidence,
    trackId: detection.track_id ?? null,
    lastSeenAt: seenAt,
  }
}

function centerDistance(first, second) {
  const firstX = (first.x1 + first.x2) / 2
  const firstY = (first.y1 + first.y2) / 2
  const secondX = (second.x1 + second.x2) / 2
  const secondY = (second.y1 + second.y2) / 2
  return Math.hypot(firstX - secondX, firstY - secondY)
}

function smoothDetection(detection, previous) {
  const currentWeight = 1 - PREVIOUS_BOX_WEIGHT
  return {
    ...detection,
    trackId: detection.trackId,
    x1: previous.x1 * PREVIOUS_BOX_WEIGHT + detection.x1 * currentWeight,
    y1: previous.y1 * PREVIOUS_BOX_WEIGHT + detection.y1 * currentWeight,
    x2: previous.x2 * PREVIOUS_BOX_WEIGHT + detection.x2 * currentWeight,
    y2: previous.y2 * PREVIOUS_BOX_WEIGHT + detection.y2 * currentWeight,
  }
}

export function updatePersonDetectionOverlay(
  previousState,
  result,
  sequence,
  now,
  gracePeriodMs,
) {
  const safePreviousState =
    previousState && typeof previousState === 'object'
      ? previousState
      : EMPTY_DETECTION_OVERLAY

  if (sequence <= safePreviousState.sequence) {
    return safePreviousState
  }

  const frameWidth =
    Number.isFinite(result?.frame_width) && result.frame_width > 0
      ? result.frame_width
      : 1
  const frameHeight =
    Number.isFinite(result?.frame_height) && result.frame_height > 0
      ? result.frame_height
      : 1
  const detections = Array.isArray(result?.detections) ? result.detections : []
  const currentDetections = detections.map((detection) =>
    normalizedDetection(detection, frameWidth, frameHeight, now),
  )
  const eligiblePrevious = Array.isArray(safePreviousState.boxes)
    ? safePreviousState.boxes.filter(
        (box) => Number.isFinite(box?.lastSeenAt) && now - box.lastSeenAt < gracePeriodMs,
      )
    : []
  const matchedPrevious = new Set()

  const boxes = currentDetections.map((detection) => {
    let matchIndex = -1
    let nearestDistance = MAX_MATCH_DISTANCE

    eligiblePrevious.forEach((previous, index) => {
      if (matchedPrevious.has(index)) {
        return
      }

      if (
        detection.trackId !== null &&
        previous.trackId !== null &&
        detection.trackId !== previous.trackId
      ) {
        return
      }

      const distance = centerDistance(detection, previous)
      if (
        detection.trackId !== null &&
        previous.trackId !== null &&
        detection.trackId === previous.trackId
      ) {
        matchIndex = index
        nearestDistance = distance
        return
      }

      if (distance < nearestDistance) {
        nearestDistance = distance
        matchIndex = index
      }
    })

    if (matchIndex < 0) {
      return detection
    }

    matchedPrevious.add(matchIndex)
    return smoothDetection(detection, eligiblePrevious[matchIndex])
  })

  boxes.push(
    ...eligiblePrevious.filter((_, index) => !matchedPrevious.has(index)),
  )

  return { sequence, boxes }
}

export function expirePersonDetectionOverlay(
  state,
  now,
  gracePeriodMs,
) {
  const safeState = state && typeof state === 'object' ? state : EMPTY_DETECTION_OVERLAY
  const boxes = (safeState.boxes ?? []).filter(
    (box) => Number.isFinite(box?.lastSeenAt) && now - box.lastSeenAt < gracePeriodMs,
  )
  return boxes.length === (safeState.boxes ?? []).length
    ? safeState
    : { ...safeState, boxes }
}

export function getNextPersonDetectionExpiry(
  state,
  now,
  gracePeriodMs,
) {
  const boxes = Array.isArray(state?.boxes) ? state.boxes : []
  if (boxes.length === 0) {
    return null
  }

  const expiries = boxes
    .filter((box) => Number.isFinite(box?.lastSeenAt))
    .map((box) => box.lastSeenAt + gracePeriodMs - now)

  if (expiries.length === 0) {
    return null
  }

  return Math.max(
    0,
    Math.min(...expiries),
  )
}

export function toVideoCoordinates(box, videoWidth, videoHeight) {
  if (!box || typeof box !== 'object') {
    return box
  }

  const safeWidth = Number.isFinite(videoWidth) && videoWidth > 0 ? videoWidth : 1
  const safeHeight = Number.isFinite(videoHeight) && videoHeight > 0 ? videoHeight : 1

  return {
    ...box,
    x1: box.x1 * safeWidth,
    y1: box.y1 * safeHeight,
    x2: box.x2 * safeWidth,
    y2: box.y2 * safeHeight,
  }
}
