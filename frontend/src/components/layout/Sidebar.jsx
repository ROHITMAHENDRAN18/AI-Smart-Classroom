import {
  Activity,
  BarChart3,
  Bell,
  BookOpen,
  CalendarCheck2,
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  Users,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'
import {
  ClipboardCheck,
} from 'lucide-react'
import {
  Timer,
} from 'lucide-react'


const navigation = [
  {
    label: 'Overview',
    path: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    label: 'Classroom',
    path: '/dashboard/classroom',
    icon: BookOpen,
  },
  {
    label: 'Students',
    path: '/dashboard/students',
    icon: Users,
  },
  {
    label: 'Attendance',
    path: '/dashboard/attendance',
    icon: ClipboardCheck,
  },
  {
    label: 'Analytics',
    path: '/dashboard/analytics',
    icon: BarChart3,
  },
  {
    label: 'Alerts',
    path: '/dashboard/alerts',
    icon: Bell,
  },
  {
    label: 'Reports',
    path: '/dashboard/reports',
    icon: Activity,
  },
{
  label: 'Session Control',
  path: '/dashboard/session',
  icon: Timer,
}
]

export default function Sidebar({
  collapsed,
  mobileOpen,
  onToggle,
  onCloseMobile,
  onLogout,
}) {
  return (
    <>
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          onClick={onCloseMobile}
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
        />
      )}

      <aside
        className={[
          'fixed inset-y-0 left-0 z-50 flex flex-col border-r border-slate-800',
          'bg-[#0a0f1c]/95 backdrop-blur-xl',
          'transition-all duration-300',
          'lg:translate-x-0',
          mobileOpen ? 'translate-x-0' : '-translate-x-full',
          collapsed ? 'w-[76px]' : 'w-[260px]',
          'lg:static lg:flex',
        ].join(' ')}
      >
        <div className="flex h-16 shrink-0 items-center border-b border-slate-800 px-4">
          <div className="flex min-w-0 flex-1 items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
              <Activity size={20} />
            </div>

            {!collapsed && (
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-white">
                  AI Smart Classroom
                </p>

                <p className="truncate text-[11px] text-slate-500">
                  Attention Monitoring
                </p>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={onToggle}
            className="hidden rounded-lg p-2 text-slate-500 transition hover:bg-slate-800 hover:text-slate-200 lg:block"
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? (
              <PanelLeftOpen size={18} />
            ) : (
              <PanelLeftClose size={18} />
            )}
          </button>

          <button
            type="button"
            onClick={onCloseMobile}
            className="rounded-lg p-2 text-slate-500 transition hover:bg-slate-800 hover:text-slate-200 lg:hidden"
            aria-label="Close sidebar"
          >
            <ChevronLeft size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-5">
          {!collapsed && (
            <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-600">
              Workspace
            </p>
          )}

          <nav className="space-y-1">
            {navigation.map((item) => {
              const Icon = item.icon

              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.path === '/dashboard'}
                  onClick={onCloseMobile}
                  title={collapsed ? item.label : undefined}
                  className={({ isActive }) =>
                    [
                      'group flex items-center gap-3 rounded-xl px-3 py-2.5',
                      'text-sm font-medium transition-all duration-200',
                      collapsed ? 'justify-center' : '',
                      isActive
                        ? 'bg-blue-500/10 text-blue-400 shadow-sm shadow-blue-500/5'
                        : 'text-slate-400 hover:bg-slate-800/70 hover:text-slate-200',
                    ].join(' ')
                  }
                >
                  {({ isActive }) => (
                    <>
                      <Icon
                        size={18}
                        className={
                          isActive
                            ? 'shrink-0 text-blue-400'
                            : 'shrink-0 text-slate-500 group-hover:text-slate-300'
                        }
                      />

                      {!collapsed && (
                        <span className="truncate">{item.label}</span>
                      )}

                      {!collapsed && isActive && (
                        <span className="ml-auto h-1.5 w-1.5 rounded-full bg-blue-400" />
                      )}
                    </>
                  )}
                </NavLink>
              )
            })}
          </nav>

          {!collapsed && (
            <div className="mt-8">
              <p className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-600">
                System
              </p>

              <NavLink
                to="/dashboard/settings"
                onClick={onCloseMobile}
                className={({ isActive }) =>
                  [
                    'group flex items-center gap-3 rounded-xl px-3 py-2.5',
                    'text-sm font-medium transition-all',
                    isActive
                      ? 'bg-blue-500/10 text-blue-400'
                      : 'text-slate-400 hover:bg-slate-800/70 hover:text-slate-200',
                  ].join(' ')
                }
              >
                <Settings size={18} />
                Settings
              </NavLink>
            </div>
          )}
        </div>

        <div className="border-t border-slate-800 p-3">
          {!collapsed ? (
            <button
              type="button"
              onClick={onLogout}
              className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-400 transition hover:bg-red-500/10 hover:text-red-400"
            >
              <LogOut size={18} />
              Logout
            </button>
          ) : (
            <button
              type="button"
              onClick={onLogout}
              title="Logout"
              className="flex w-full items-center justify-center rounded-xl px-3 py-2.5 text-slate-400 transition hover:bg-red-500/10 hover:text-red-400"
            >
              <LogOut size={18} />
            </button>
          )}
        </div>
      </aside>
    </>
  )
}
