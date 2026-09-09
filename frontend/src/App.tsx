import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Navbar from './components/Navbar'
import { api } from './lib/api'
import Dashboard from './pages/Dashboard'
import History from './pages/History'
import Login from './pages/Login'
import Logs from './pages/Logs'
import Settings from './pages/Settings'

export default function App() {
  const [authed, setAuthed] = useState<boolean | null>(null)

  useEffect(() => {
    api.controlStatus().then(() => setAuthed(true)).catch(() => setAuthed(false))
  }, [])

  if (authed === null) {
    return <div className="flex min-h-screen items-center justify-center text-slate-500">جاري التحميل...</div>
  }

  if (!authed) {
    return <Login onLogin={() => setAuthed(true)} />
  }

  return (
    <div className="min-h-screen">
      <Navbar onLogout={() => setAuthed(false)} />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/history" element={<History />} />
        <Route path="/logs" element={<Logs />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}
