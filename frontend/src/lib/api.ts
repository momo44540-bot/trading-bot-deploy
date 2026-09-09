async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    ...options,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export type Position = {
  id: number
  symbol: string
  entry_price: number
  current_price: number
  size: number
  quote_spent: number
  take_profit_price: number
  stop_loss_price: number
  unrealized_pct: number
  entry_time: string
  mode: string
}

export type Dashboard = {
  running: boolean
  kill_switch: boolean
  trading_mode: 'paper' | 'live'
  available_balance: number | null
  daily_realized_pnl_pct: number
  daily_loss_limit_hit: boolean
  open_positions: Position[]
}

export type Trade = {
  id: number
  symbol: string
  entry_price: number
  exit_price: number
  size: number
  quote_spent: number
  pnl_quote: number
  pnl_pct: number
  exit_reason: string
  mode: string
  entry_time: string
  exit_time: string
}

export type DecisionLogEntry = {
  id: number
  timestamp: string
  symbol: string
  decision: string
  reason: string
  details: Record<string, unknown>
}

export type StrategySettings = {
  symbols: string[]
  timeframe: string
  take_profit_pct: number
  stop_loss_pct: number
  position_size_pct: number
  max_concurrent_positions: number
  orderbook_depth_levels: number
  orderbook_ratio_threshold: number
  volume_avg_lookback: number
  volume_ratio_threshold: number
  daily_loss_limit_pct: number
  okx_keys_configured: boolean
  okx_demo: boolean
  note: string
}

export const api = {
  login: (password: string) => request<{ ok: boolean }>('/api/auth/login', {
    method: 'POST', body: JSON.stringify({ password }),
  }),
  logout: () => request<{ ok: boolean }>('/api/auth/logout', { method: 'POST' }),
  getDashboard: () => request<Dashboard>('/api/dashboard'),
  getSettings: () => request<StrategySettings>('/api/settings'),
  updateSettings: (payload: Partial<StrategySettings>) => request<{ ok: boolean }>('/api/settings', {
    method: 'PUT', body: JSON.stringify(payload),
  }),
  getTrades: () => request<Trade[]>('/api/trades'),
  getLogs: () => request<DecisionLogEntry[]>('/api/trades/logs'),
  controlStatus: () => request<{ running: boolean; kill_switch: boolean; trading_mode: string }>('/api/control/status'),
  start: () => request<{ ok: boolean }>('/api/control/start', { method: 'POST' }),
  stop: () => request<{ ok: boolean }>('/api/control/stop', { method: 'POST' }),
  killSwitch: (enabled: boolean, closePositions: boolean) => request<{ ok: boolean }>('/api/control/kill-switch', {
    method: 'POST', body: JSON.stringify({ enabled, close_positions: closePositions }),
  }),
  setMode: (mode: 'paper' | 'live') => request<{ ok: boolean }>('/api/control/mode', {
    method: 'POST', body: JSON.stringify({ mode }),
  }),
  closeAll: () => request<{ ok: boolean }>('/api/control/close-all', { method: 'POST' }),
}
