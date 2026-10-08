import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  clearAuthSession,
  getAccessToken,
  getCurrentUser,
  getStoredUser,
  login as loginRequest,
  saveAuthSession,
} from '../services/authService'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => getStoredUser())
  const [token, setToken] = useState(() => getAccessToken())
  const [loading, setLoading] = useState(true)

  const logout = useCallback(() => {
    clearAuthSession()
    setUser(null)
    setToken(null)
  }, [])

  useEffect(() => {
    let mounted = true

    async function restoreSession() {
      const storedToken = getAccessToken()

      if (!storedToken) {
        if (mounted) {
          setLoading(false)
        }

        return
      }

      try {
        const currentUser = await getCurrentUser(storedToken)

        if (!mounted) {
          return
        }

        setToken(storedToken)
        setUser(currentUser)
      } catch {
        if (mounted) {
          logout()
        }
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    restoreSession()

    return () => {
      mounted = false
    }
  }, [logout])

  const login = useCallback(async (username, password) => {
    const data = await loginRequest(username, password)

    saveAuthSession(data)

    setToken(data.access_token)
    setUser(data.user)

    return data
  }, [])

  const value = useMemo(
    () => ({
      user,
      token,
      loading,
      isAuthenticated: Boolean(token && user),
      login,
      logout,
    }),
    [user, token, loading, login, logout],
  )

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider')
  }

  return context
}
