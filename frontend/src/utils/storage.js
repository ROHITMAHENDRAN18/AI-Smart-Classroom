export function getStoredItem(key, fallback = null) {
  try {
    const item = localStorage.getItem(key)
    return item !== null ? item : fallback
  } catch {
    return fallback
  }
}

export function setStoredItem(key, value) {
  try {
    localStorage.setItem(key, value)
  } catch (error) {
    console.error(`Error saving ${key} to localStorage:`, error)
  }
}

export function removeStoredItem(key) {
  try {
    localStorage.removeItem(key)
  } catch (error) {
    console.error(`Error removing ${key} from localStorage:`, error)
  }
}
