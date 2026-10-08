import { Activity } from 'lucide-react'

export default function LiveMonitoring() {
  return (
    <div className="min-h-screen bg-[#070b14] p-6">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
            <Activity size={22} />
          </div>

          <div>
            <h1 className="text-2xl font-bold text-white">
              Live Monitoring
            </h1>

            <p className="mt-1 text-sm text-slate-400">
              Monitor classroom activity in real time.
            </p>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />

            <span className="text-sm font-medium text-emerald-400">
              Live Monitoring Ready
            </span>
          </div>

          <p className="mt-4 text-sm text-slate-400">
            The Live Monitoring page is connected to the dashboard route.
          </p>
        </div>
      </div>
    </div>
  )
}