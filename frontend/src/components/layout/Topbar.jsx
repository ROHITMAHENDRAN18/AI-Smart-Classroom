import {
  Bell,
  Menu,
  ShieldCheck,
} from 'lucide-react'
import { useLocation } from 'react-router-dom'

import { useAuth } from '../../context/AuthContext'

const pageTitles = {
  '/dashboard': {
    title: 'Dashboard',
    description: 'Classroom monitoring overview',
  },
  '/dashboard/classroom': {
    title: 'Classroom',
    description: 'Live classroom monitoring',
  },
  '/dashboard/students': {
    title: 'Students',
    description: 'Student attention and attendance',
  },
  '/dashboard/attendance': {
    title: 'Attendance',
    description: 'Attendance records and history',
  },
  '/dashboard/analytics': {
    title: 'Analytics',
    description: 'Classroom attention analytics',
  },
  '/dashboard/alerts': {
    title: 'Alerts',
    description: 'Attention and classroom alerts',
  },
  '/dashboard/reports': {
    title: 'Reports',
    description: 'Student and classroom reports',
  },
  '/dashboard/settings': {
    title: 'Settings',
    description: 'System preferences',
  },
}

export default function Topbar({ onOpenMobile }) {
  const location = useLocation()
  const { user } = useAuth()

  const page =
    pageTitles[location.pathname] || pageTitles['/dashboard']

  const displayName =
    user?.name ||
    user?.username ||
    'Teacher'

  const initials = displayName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('')

  return (
    <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center justify-between border-b border-slate-800 bg-[#070b14]/85 px-4 backdrop-blur-xl sm:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          onClick={onOpenMobile}
          className="rounded-lg p-2 text-slate-400 transition hover:bg-slate-800 hover:text-white lg:hidden"
          aria-label="Open navigation"
        >
          <Menu size={21} />
        </button>

        <div className="min-w-0">
          <h1 className="truncate text-sm font-semibold text-white sm:text-base">
            {page.title}
          </h1>

          <p className="hidden truncate text-xs text-slate-500 sm:block">
            {page.description}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-4">
        <div className="hidden items-center gap-2 rounded-full border border-emerald-500/15 bg-emerald-500/5 px-3 py-1.5 sm:flex">
          <span className="status-dot status-dot-success" />

          <span className="text-xs font-medium text-emerald-400">
            System online
          </span>
        </div>

        <button
          type="button"
          className="relative rounded-xl border border-slate-800 bg-slate-900/70 p-2.5 text-slate-400 transition hover:border-slate-700 hover:bg-slate-800 hover:text-white"
          aria-label="Notifications"
        >
          <Bell size={18} />

          <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-blue-400" />
        </button>

        <div className="hidden h-7 w-px bg-slate-800 sm:block" />

        <div className="flex items-center gap-2.5">
          <div className="hidden text-right sm:block">
            <p className="max-w-[150px] truncate text-xs font-medium text-slate-200">
              {displayName}
            </p>

            <div className="mt-0.5 flex items-center justify-end gap-1 text-[10px] text-slate-500">
              <ShieldCheck size={11} />
              Teacher
            </div>
          </div>

          <div className="flex h-9 w-9 items-center justify-center rounded-full border border-blue-500/20 bg-blue-500/10 text-xs font-bold text-blue-400">
            {initials || 'T'}
          </div>
        </div>
      </div>
    </header>
  )
}
