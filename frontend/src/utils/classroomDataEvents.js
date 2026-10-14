const CLASSROOM_DATA_CHANGED_EVENT = 'classroom-data-changed'

export function notifyClassroomDataChanged() {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(CLASSROOM_DATA_CHANGED_EVENT))
  }
}

export function subscribeToClassroomDataChanges(listener) {
  if (typeof window === 'undefined') {
    return () => {}
  }

  window.addEventListener(CLASSROOM_DATA_CHANGED_EVENT, listener)
  return () =>
    window.removeEventListener(CLASSROOM_DATA_CHANGED_EVENT, listener)
}
