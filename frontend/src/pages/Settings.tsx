import { useEffect, useState } from 'react'
import { api, type StrategySettings } from '../lib/api'

export default function Settings() {
  const [form, setForm] = useState<StrategySettings | null>(null)
  const [symbolsText, setSymbolsText] = useState('')
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getSettings().then((s) => {
      setForm(s)
      setSymbolsText(s.symbols.join(', '))
    })
  }, [])

  if (!form) return <div className="p-6 text-slate-400">جاري التحميل...</div>

  function update<K extends keyof StrategySettings>(key: K, value: StrategySettings[K]) {
    setForm((prev) => (prev ? { ...prev, [key]: value } : prev))
  }

  async function save() {
    if (!form) return
    setError('')
    setSaved(false)
    try {
      const symbols = symbolsText.split(',').map((s) => s.trim().toUpperCase()).filter(Boolean)
      await api.updateSettings({ ...form, symbols })
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch {
      setError('فشل حفظ الإعدادات')
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-4 p-4">
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 text-sm text-slate-400">
        <p>{form.note}</p>
        <p className="mt-2">
          مفاتيح OKX: {form.okx_keys_configured ? (
            <span className="text-emerald-400">مُعدّة ✓</span>
          ) : (
            <span className="text-amber-400">غير مُعدّة — عدّل backend/.env</span>
          )}
          {' · '}
          الوضع: {form.okx_demo ? 'OKX Demo' : 'OKX الحقيقي'}
        </p>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 space-y-4">
        <Field label="الأزواج (مفصولة بفاصلة)">
          <input value={symbolsText} onChange={(e) => setSymbolsText(e.target.value)}
            placeholder="BTC-USDT, ETH-USDT, SOL-USDT"
            className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-white outline-none focus:border-emerald-500" />
        </Field>

        <div className="grid grid-cols-2 gap-4">
          <NumberField label="جني الربح %" value={form.take_profit_pct}
            onChange={(v) => update('take_profit_pct', v)} />
          <NumberField label="وقف الخسارة %" value={form.stop_loss_pct}
            onChange={(v) => update('stop_loss_pct', v)} />
          <NumberField label="حجم الصفقة % من رأس المال" value={form.position_size_pct}
            onChange={(v) => update('position_size_pct', v)} />
          <NumberField label="أقصى صفقات متزامنة" value={form.max_concurrent_positions}
            onChange={(v) => update('max_concurrent_positions', v)} />
          <NumberField label="حد الخسارة اليومي %" value={form.daily_loss_limit_pct}
            onChange={(v) => update('daily_loss_limit_pct', v)} />
          <NumberField label="مستويات دفتر الأوامر" value={form.orderbook_depth_levels}
            onChange={(v) => update('orderbook_depth_levels', v)} />
          <NumberField label="حد نسبة ضغط الدفتر" value={form.orderbook_ratio_threshold}
            onChange={(v) => update('orderbook_ratio_threshold', v)} step={0.1} />
          <NumberField label="متوسط الحجم (عدد الشموع)" value={form.volume_avg_lookback}
            onChange={(v) => update('volume_avg_lookback', v)} />
          <NumberField label="حد نسبة الحجم" value={form.volume_ratio_threshold}
            onChange={(v) => update('volume_ratio_threshold', v)} step={0.1} />
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}
        {saved && <p className="text-sm text-emerald-400">تم الحفظ ✓</p>}

        <button onClick={save}
          className="w-full rounded-lg bg-emerald-600 px-4 py-2 font-medium text-white hover:bg-emerald-500">
          حفظ الإعدادات
        </button>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-slate-400">{label}</span>
      {children}
    </label>
  )
}

function NumberField({ label, value, onChange, step = 1 }: {
  label: string; value: number; onChange: (v: number) => void; step?: number
}) {
  return (
    <Field label={label}>
      <input type="number" step={step} value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-white outline-none focus:border-emerald-500" />
    </Field>
  )
}
