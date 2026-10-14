const MAX_MATCH_DISTANCE = 0.25
const PREVIOUS_BOX_WEIGHT = 0.35

export const EMPTY_DETECTION_OVERLAY = {
  sequence: 0,
  boxes: [],
}

function normalizedDetection(detection, frameWidth, frameHeight, seenAt) {
  return {
    x1: detection.x1 / frameWidth,
    y1: detection.y1 / frameHeight,
    x2: detection.x2 / frameWidth,
    y2: detection.y2 / frameHeight,
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
  if (sequence <= previousState.sequence) {
    return previousState
  }

  const currentDetections = result.detections.map((detection) =>
    normalizedDetection(
      detection,
      result.frame_width,
      result.frame_height,
      now,
    ),
  )
  const eligiblePrevious = previousState.boxes.filter(
    (box) => now - box.lastSeenAt < gracePeriodMs,
  )
  const matchedPrevious = new Set()

  const boxes = currentDetections.map((detection) => {
    let matchIndex = -1
    let nearestDistance = MAX_MATCH_DISTANCE

    eligiblePrevious.forEach((previous, index) => {
      if (matchedPrevious.has(index)) {
        return
      }
      const distance = centerDistance(detection, previous)
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
  const boxes = state.boxes.filter(
    (box) => now - box.lastSeenAt < gracePeriodMs,
  )
  return boxes.length === state.boxes.length
    ? state
    : { ...state, boxes }
}

export function getNextPersonDetectionExpiry(
  state,
  now,
  gracePeriodMs,
) {
  if (state.boxes.length === 0) {
    return null
  }

  return Math.max(
    0,
    Math.min(
      ...state.boxes.map(
        (box) => box.lastSeenAt + gracePeriodMs - now,
      ),
    ),
  )
}

export function toVideoCoordinates(box, videoWidth, videoHeight) {
  return {
    ...box,
    x1: box.x1 * videoWidth,
    y1: box.y1 * videoHeight,
    x2: box.x2 * videoWidth,
    y2: box.y2 * videoHeight,
  }
}
