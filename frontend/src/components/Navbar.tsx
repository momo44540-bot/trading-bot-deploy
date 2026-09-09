import { NavLink } from 'react-router-dom'
import { api } from '../lib/api'

const links = [
  { to: '/', label: 'لوحة التحكم' },
  { to: '/history', label: 'السجل' },
  { to: '/logs', label: 'قرارات البوت' },
  { to: '/settings', label: 'الإعدادات' },
]

export default function Navbar({ onLogout }: { onLogout: () => void }) {
  return (
    <nav className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 bg-slate-950/95 px-4 py-3 backdrop-blur">
      <div className="flex flex-wrap gap-1">
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.to === '/'}
            className={({ isActive }) =>
              `rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive ? 'bg-emerald-600 text-white' : 'text-slate-300 hover:bg-slate-800'
              }`
            }
          >
            {l.label}
          </NavLink>
        ))}
      </div>
      <button
        onClick={async () => {
          await api.logout()
          onLogout()
        }}
        className="rounded-lg px-3 py-2 text-sm text-slate-400 hover:bg-slate-800 hover:text-white"
      >
        تسجيل خروج
      </button>
    </nav>
  )
}
