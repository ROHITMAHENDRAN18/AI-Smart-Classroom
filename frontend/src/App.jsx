import { Navigate, Route, Routes } from 'react-router-dom'

import ProtectedRoute from './components/common/ProtectedRoute'
import DashboardLayout from './components/layout/DashboardLayout'
import { useAuth } from './context/AuthContext'
import Dashboard from './pages/Dashboard'
import ClassroomOverview from './pages/ClassroomOverview'
import Login from './pages/Login'
import LiveMonitoring from './pages/LiveMonitoring'
import StudentAttention from './pages/StudentAttention'
import Attendance from './pages/Attendance'
import SessionControl from './pages/SessionControl'
import Alerts from './pages/Alerts'
function App() {
  const { isAuthenticated } = useAuth()

  return (
    <Routes>
      <Route
        path="/login"
        element={
          isAuthenticated ? (
            <Navigate to="/dashboard" replace />
          ) : (
            <Login />
          )
        }
      />

     <Route element={<ProtectedRoute />}>
  <Route element={<DashboardLayout />}>
    <Route
      path="/dashboard"
      element={<Dashboard />}
    />

    <Route
      path="/dashboard/classroom"
      element={<ClassroomOverview />}
    />

    <Route
      path="/dashboard/live"
      element={<LiveMonitoring />}
    />

    <Route
      path="/dashboard/students/attention"
      element={<StudentAttention />}
    />
  </Route>
  <Route
  path="/dashboard/attendance"
  element={<Attendance />}
/>
<Route
  path="/dashboard/session"
  element={<SessionControl />}
/>
<Route
  path="/dashboard/alerts"
  element={<Alerts />}
/>
</Route>


      <Route
        path="*"
        element={
          <Navigate
            to={isAuthenticated ? '/dashboard' : '/login'}
            replace
          />
        }
      />
    </Routes>
  )
}

export default App
