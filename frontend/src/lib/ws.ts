import { useEffect, useRef } from 'react'

export type LiveMessage = {
  type: string
  symbol?: string
  decision?: string
  reason?: string
  details?: Record<string, unknown>
  timestamp?: string
}

export function useLiveFeed(onMessage: (msg: LiveMessage) => void) {
  const handlerRef = useRef(onMessage)
  handlerRef.current = onMessage

  useEffect(() => {
    let ws: WebSocket | null = null
    let closedByCleanup = false
    let retryTimer: ReturnType<typeof setTimeout> | null = null

    const connect = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      ws = new WebSocket(`${protocol}//${window.location.host}/ws/live`)
      ws.onmessage = (event) => {
        try {
          handlerRef.current(JSON.parse(event.data))
        } catch {
          // ignore malformed message
        }
      }
      ws.onclose = () => {
        if (!closedByCleanup) {
          retryTimer = setTimeout(connect, 3000)
        }
      }
    }

    connect()
    return () => {
      closedByCleanup = true
      if (retryTimer) clearTimeout(retryTimer)
      ws?.close()
    }
  }, [])
}
