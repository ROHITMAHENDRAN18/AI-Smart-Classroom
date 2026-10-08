import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from '../../context/AuthContext'

export default function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#070b14]">
        <div className="flex items-center gap-3 text-sm text-slate-400">
          <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-blue-500" />
          Restoring session...
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname }}
      />
    )
  }

  return <Outlet />
}
