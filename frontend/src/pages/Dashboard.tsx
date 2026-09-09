import { useCallback, useEffect, useState } from 'react'
import { api, type Dashboard as DashboardData } from '../lib/api'
import { useLiveFeed } from '../lib/ws'

function fmt(n: number | null | undefined, digits = 2) {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  return n.toLocaleString('en-US', { maximumFractionDigits: digits, minimumFractionDigits: digits })
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      setData(await api.getDashboard())
    } catch {
      setError('تعذر تحميل بيانات اللوحة')
    }
  }, [])

  useEffect(() => {
    load()
    const interval = setInterval(load, 5000)
    return () => clearInterval(interval)
  }, [load])

  useLiveFeed((msg) => {
    if (msg.type === 'position_opened' || msg.type === 'position_closed') load()
  })

  async function withBusy(fn: () => Promise<unknown>) {
    setBusy(true)
    setError('')
    try {
      await fn()
      await load()
    } catch {
      setError('فشل تنفيذ العملية')
    } finally {
      setBusy(false)
    }
  }

  if (!data) return <div className="p-6 text-slate-400">جاري التحميل...</div>

  const modeIsLive = data.trading_mode === 'live'

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-4">
      {error && <div className="rounded-lg bg-red-950 px-4 py-2 text-sm text-red-300">{error}</div>}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="حالة البوت" value={data.running ? 'يعمل' : 'متوقف'}
          tone={data.running ? 'good' : 'neutral'} />
        <StatCard label="الوضع" value={modeIsLive ? 'حقيقي (Live)' : 'محاكاة (Paper)'}
          tone={modeIsLive ? 'warn' : 'neutral'} />
        <StatCard label="الرصيد المتاح" value={`$${fmt(data.available_balance)}`} tone="neutral" />
        <StatCard label="ربح/خسارة اليوم" value={`${fmt(data.daily_realized_pnl_pct)}%`}
          tone={data.daily_realized_pnl_pct >= 0 ? 'good' : 'bad'} />
      </div>

      {data.kill_switch && (
        <div className="rounded-lg bg-red-950 px-4 py-2 text-sm text-red-300">
          مفتاح الإيقاف الطارئ مُفعّل — لا يتم فتح صفقات جديدة.
        </div>
      )}
      {data.daily_loss_limit_hit && (
        <div className="rounded-lg bg-amber-950 px-4 py-2 text-sm text-amber-300">
          تم بلوغ حد الخسارة اليومي — تم إيقاف الدخول في صفقات جديدة حتى اليوم التالي.
        </div>
      )}

      <div className="flex flex-wrap gap-2 rounded-xl border border-slate-800 bg-slate-900 p-4">
        <button disabled={busy || data.running} onClick={() => withBusy(api.start)}
          className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:opacity-40">
          تشغيل البوت
        </button>
        <button disabled={busy || !data.running} onClick={() => withBusy(api.stop)}
          className="rounded-lg bg-slate-700 px-4 py-2 text-sm font-medium text-white hover:bg-slate-600 disabled:opacity-40">
          إيقاف البوت
        </button>
        <button disabled={busy}
          onClick={() => withBusy(() => api.killSwitch(!data.kill_switch, false))}
          className="rounded-lg bg-red-700 px-4 py-2 text-sm font-medium text-white hover:bg-red-600 disabled:opacity-40">
          {data.kill_switch ? 'إلغاء الإيقاف الطارئ' : 'تفعيل الإيقاف الطارئ'}
        </button>
        <button disabled={busy || data.open_positions.length === 0}
          onClick={() => {
            if (confirm('هل أنت متأكد من إغلاق كل الصفقات المفتوحة الآن؟')) withBusy(api.closeAll)
          }}
          className="rounded-lg bg-slate-700 px-4 py-2 text-sm font-medium text-white hover:bg-slate-600 disabled:opacity-40">
          إغلاق كل الصفقات
        </button>
        <button disabled={busy}
          onClick={() => {
            const target = modeIsLive ? 'paper' : 'live'
            const msg = target === 'live'
              ? 'سيبدأ البوت بتنفيذ صفقات حقيقية بأموالك الفعلية على OKX. هل أنت متأكد؟'
              : 'سيتحول البوت لوضع المحاكاة (بدون أموال حقيقية). متابعة؟'
            if (confirm(msg)) withBusy(() => api.setMode(target))
          }}
          className={`rounded-lg px-4 py-2 text-sm font-medium text-white disabled:opacity-40 ${
            modeIsLive ? 'bg-slate-700 hover:bg-slate-600' : 'bg-amber-700 hover:bg-amber-600'
          }`}>
          {modeIsLive ? 'التحويل لوضع المحاكاة' : 'التحويل للتداول الحقيقي'}
        </button>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
        <h2 className="mb-3 font-semibold text-white">الصفقات المفتوحة ({data.open_positions.length})</h2>
        {data.open_positions.length === 0 ? (
          <p className="text-sm text-slate-500">لا توجد صفقات مفتوحة حاليًا.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[600px] text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-right text-slate-400">
                  <th className="py-2">الزوج</th>
                  <th>سعر الدخول</th>
                  <th>السعر الحالي</th>
                  <th>الربح/الخسارة</th>
                  <th>جني الربح</th>
                  <th>وقف الخسارة</th>
                </tr>
              </thead>
              <tbody>
                {data.open_positions.map((p) => (
                  <tr key={p.id} className="border-b border-slate-800/50">
                    <td className="py-2 font-medium text-white">{p.symbol}</td>
                    <td>{fmt(p.entry_price, 4)}</td>
                    <td>{fmt(p.current_price, 4)}</td>
                    <td className={p.unrealized_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                      {fmt(p.unrealized_pct)}%
                    </td>
                    <td className="text-slate-400">{fmt(p.take_profit_price, 4)}</td>
                    <td className="text-slate-400">{fmt(p.stop_loss_price, 4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({ label, value, tone }: { label: string; value: string; tone: 'good' | 'bad' | 'warn' | 'neutral' }) {
  const toneClass = {
    good: 'text-emerald-400', bad: 'text-red-400', warn: 'text-amber-400', neutral: 'text-white',
  }[tone]
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`mt-1 text-lg font-bold ${toneClass}`}>{value}</p>
    </div>
  )
}
