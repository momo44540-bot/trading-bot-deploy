import { useEffect, useState } from 'react'
import { api, type DecisionLogEntry } from '../lib/api'
import { useLiveFeed } from '../lib/ws'

const decisionStyle: Record<string, string> = {
  entry: 'bg-emerald-950 text-emerald-300 border-emerald-900',
  exit: 'bg-sky-950 text-sky-300 border-sky-900',
  reject: 'bg-slate-800 text-slate-400 border-slate-700',
  error: 'bg-red-950 text-red-300 border-red-900',
  info: 'bg-slate-800 text-slate-300 border-slate-700',
}

const decisionLabel: Record<string, string> = {
  entry: 'دخول',
  exit: 'خروج',
  reject: 'رفض',
  error: 'خطأ',
  info: 'معلومة',
}

export default function Logs() {
  const [logs, setLogs] = useState<DecisionLogEntry[]>([])

  useEffect(() => {
    api.getLogs().then(setLogs).catch(() => {})
  }, [])

  useLiveFeed((msg) => {
    if (msg.type === 'decision') {
      setLogs((prev) => [
        {
          id: Math.random(),
          timestamp: msg.timestamp ?? new Date().toISOString(),
          symbol: msg.symbol ?? '',
          decision: msg.decision ?? 'info',
          reason: msg.reason ?? '',
          details: msg.details ?? {},
        },
        ...prev,
      ].slice(0, 300))
    }
  })

  return (
    <div className="mx-auto max-w-4xl space-y-2 p-4">
      <h2 className="mb-2 font-semibold text-white">سجل قرارات البوت (حي)</h2>
      {logs.length === 0 && <p className="text-sm text-slate-500">لا توجد قرارات بعد. شغّل البوت من لوحة التحكم.</p>}
      {logs.map((log) => (
        <div key={log.id} className={`rounded-lg border px-3 py-2 text-sm ${decisionStyle[log.decision] ?? decisionStyle.info}`}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-medium">
              [{decisionLabel[log.decision] ?? log.decision}] {log.symbol} — {log.reason}
            </span>
            <span className="text-xs opacity-60">{new Date(log.timestamp).toLocaleTimeString('ar-EG')}</span>
          </div>
          {Object.keys(log.details ?? {}).length > 0 && (
            <div className="mt-1 flex flex-wrap gap-3 text-xs opacity-70">
              {Object.entries(log.details).map(([k, v]) => (
                <span key={k}>{k}: {typeof v === 'number' ? v.toFixed(4) : String(v)}</span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
