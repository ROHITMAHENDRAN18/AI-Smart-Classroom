import { useState } from 'react'
import { Activity, Eye, EyeOff, LockKeyhole, Mail, UserPlus, UserRound } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '../context/AuthContext'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()

  const { login, register } = useAuth()

  const [isRegister, setIsRegister] = useState(false)
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [role, setRole] = useState('TEACHER')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const from = location.state?.from || '/dashboard'

  function switchMode(registerMode) {
    setIsRegister(registerMode)
    setError('')
    setPassword('')
    setConfirmPassword('')
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')

    const trimmedUsername = username.trim()
    const trimmedEmail = email.trim()

    if (!trimmedUsername || !password) {
      setError('Please fill in all required fields.')
      return
    }

    if (isRegister) {
      if (!trimmedEmail) {
        setError('Please enter your email address.')
        return
      }

      if (trimmedUsername.length < 3) {
        setError('Username must be at least 3 characters.')
        return
      }

      if (password.length < 6) {
        setError('Password must be at least 6 characters.')
        return
      }

      if (password !== confirmPassword) {
        setError('Passwords do not match.')
        return
      }
    }

    try {
      setSubmitting(true)

      if (isRegister) {
        await register(trimmedUsername, trimmedEmail, password, role)
      } else {
        await login(trimmedUsername, password)
      }

      navigate(from, { replace: true })
    } catch (requestError) {
      const detail = requestError.response?.data?.detail

      if (typeof detail === 'string') {
        setError(detail)
      } else if (Array.isArray(detail)) {
        setError(detail.map((d) => d.msg || d).join(', '))
      } else {
        setError(
          isRegister
            ? 'Registration failed. Please check your information.'
            : 'Invalid username or password.'
        )
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-[#070b14]">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-[-10%] top-[-15%] h-[500px] w-[500px] rounded-full bg-blue-500/10 blur-3xl" />
        <div className="absolute bottom-[-20%] right-[-10%] h-[500px] w-[500px] rounded-full bg-cyan-500/8 blur-3xl" />
      </div>

      <div className="relative mx-auto flex min-h-screen max-w-7xl items-center justify-center px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid w-full max-w-5xl overflow-hidden rounded-2xl border border-slate-800 bg-slate-950/80 shadow-2xl shadow-black/30 lg:grid-cols-2">
          <section className="hidden flex-col justify-between border-r border-slate-800 bg-gradient-to-br from-blue-500/10 via-slate-950 to-cyan-500/5 p-10 lg:flex">
            <div>
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
                  <Activity size={23} />
                </div>

                <div>
                  <p className="text-sm font-semibold text-white">
                    AI Smart Classroom
                  </p>

                  <p className="text-xs text-slate-500">
                    Intelligent classroom monitoring
                  </p>
                </div>
              </div>

              <div className="mt-20">
                <p className="text-sm font-medium uppercase tracking-[0.2em] text-blue-400">
                  Teacher Portal
                </p>

                <h1 className="mt-4 text-4xl font-bold leading-tight tracking-tight text-white">
                  Monitor your classroom
                  <span className="text-gradient"> intelligently.</span>
                </h1>

                <p className="mt-5 max-w-md text-sm leading-7 text-slate-400">
                  Track attendance, attention states, classroom activity,
                  alerts, analytics, and session history from one platform.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span className="status-dot status-dot-success" />
              AI monitoring platform
            </div>
          </section>

          <section className="flex items-center justify-center p-6 sm:p-10">
            <div className="w-full max-w-md">
              <div className="mb-6 lg:hidden">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
                    <Activity size={23} />
                  </div>

                  <div>
                    <p className="text-sm font-semibold text-white">
                      AI Smart Classroom
                    </p>

                    <p className="text-xs text-slate-500">
                      Intelligent classroom monitoring
                    </p>
                  </div>
                </div>
              </div>

              <div className="mb-6 flex rounded-xl border border-slate-800 bg-slate-900/60 p-1">
                <button
                  type="button"
                  onClick={() => switchMode(false)}
                  className={`flex-1 rounded-lg py-2 text-xs font-semibold transition ${
                    !isRegister
                      ? 'bg-blue-500 text-white shadow-sm shadow-blue-500/20'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Sign in
                </button>
                <button
                  type="button"
                  onClick={() => switchMode(true)}
                  className={`flex-1 rounded-lg py-2 text-xs font-semibold transition ${
                    isRegister
                      ? 'bg-blue-500 text-white shadow-sm shadow-blue-500/20'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Create account
                </button>
              </div>

              <div>
                <p className="text-sm font-medium text-blue-400">
                  {isRegister ? 'Get started' : 'Welcome back'}
                </p>

                <h2 className="mt-2 text-3xl font-bold tracking-tight text-white">
                  {isRegister ? 'Create an account' : 'Sign in'}
                </h2>

                <p className="mt-2 text-sm text-slate-400">
                  {isRegister
                    ? 'Register your account to manage your classroom.'
                    : 'Sign in to access your classroom dashboard.'}
                </p>
              </div>

              <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                <div>
                  <label
                    htmlFor="username"
                    className="mb-1.5 block text-xs font-medium text-slate-300"
                  >
                    Username
                  </label>

                  <div className="relative">
                    <UserRound
                      size={18}
                      className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
                    />

                    <input
                      id="username"
                      type="text"
                      autoComplete="username"
                      value={username}
                      onChange={(event) => setUsername(event.target.value)}
                      placeholder="e.g. teacher_john"
                      className="w-full rounded-xl border border-slate-700 bg-slate-900/70 py-2.5 pl-10 pr-4 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                    />
                  </div>
                </div>

                {isRegister && (
                  <div>
                    <label
                      htmlFor="email"
                      className="mb-1.5 block text-xs font-medium text-slate-300"
                    >
                      Email address
                    </label>

                    <div className="relative">
                      <Mail
                        size={18}
                        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
                      />

                      <input
                        id="email"
                        type="email"
                        autoComplete="email"
                        value={email}
                        onChange={(event) => setEmail(event.target.value)}
                        placeholder="teacher@school.edu"
                        className="w-full rounded-xl border border-slate-700 bg-slate-900/70 py-2.5 pl-10 pr-4 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                      />
                    </div>
                  </div>
                )}

                <div>
                  <label
                    htmlFor="password"
                    className="mb-1.5 block text-xs font-medium text-slate-300"
                  >
                    Password
                  </label>

                  <div className="relative">
                    <LockKeyhole
                      size={18}
                      className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
                    />

                    <input
                      id="password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete={isRegister ? 'new-password' : 'current-password'}
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      placeholder={isRegister ? 'At least 6 characters' : 'Enter your password'}
                      className="w-full rounded-xl border border-slate-700 bg-slate-900/70 py-2.5 pl-10 pr-11 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                    />

                    <button
                      type="button"
                      onClick={() => setShowPassword((value) => !value)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 transition hover:text-slate-300"
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>

                {isRegister && (
                  <div>
                    <label
                      htmlFor="confirmPassword"
                      className="mb-1.5 block text-xs font-medium text-slate-300"
                    >
                      Confirm password
                    </label>

                    <div className="relative">
                      <LockKeyhole
                        size={18}
                        className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
                      />

                      <input
                        id="confirmPassword"
                        type={showPassword ? 'text' : 'password'}
                        autoComplete="new-password"
                        value={confirmPassword}
                        onChange={(event) => setConfirmPassword(event.target.value)}
                        placeholder="Re-enter your password"
                        className="w-full rounded-xl border border-slate-700 bg-slate-900/70 py-2.5 pl-10 pr-4 text-sm text-white outline-none transition placeholder:text-slate-600 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                      />
                    </div>
                  </div>
                )}

                {isRegister && (
                  <div>
                    <label
                      htmlFor="role"
                      className="mb-1.5 block text-xs font-medium text-slate-300"
                    >
                      Account Role
                    </label>

                    <select
                      id="role"
                      value={role}
                      onChange={(e) => setRole(e.target.value)}
                      className="w-full rounded-xl border border-slate-700 bg-slate-900/70 py-2.5 px-3 text-sm text-white outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                    >
                      <option value="TEACHER">Teacher</option>
                      <option value="ADMIN">Admin</option>
                    </select>
                  </div>
                )}

                {error && (
                  <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-2.5 text-xs text-red-400">
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={submitting}
                  className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-blue-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {submitting ? (
                    isRegister ? 'Creating account...' : 'Signing in...'
                  ) : isRegister ? (
                    <>
                      <UserPlus size={17} />
                      Create Account
                    </>
                  ) : (
                    'Sign in'
                  )}
                </button>
              </form>

              <div className="mt-6 text-center">
                <button
                  type="button"
                  onClick={() => switchMode(!isRegister)}
                  className="text-xs text-slate-400 hover:text-blue-400 transition"
                >
                  {isRegister ? (
                    <>
                      Already have an account?{' '}
                      <span className="font-semibold text-blue-400 underline underline-offset-4">
                        Sign in
                      </span>
                    </>
                  ) : (
                    <>
                      Don't have an account?{' '}
                      <span className="font-semibold text-blue-400 underline underline-offset-4">
                        Create an account
                      </span>
                    </>
                  )}
                </button>
              </div>

              <p className="mt-8 text-center text-xs text-slate-600">
                Secure access to the classroom monitoring platform
              </p>
            </div>
          </section>
        </div>
      </div>
    </main>
  )
}
