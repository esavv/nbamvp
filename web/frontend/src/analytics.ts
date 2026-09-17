const ANALYTICS_ID_KEY = 'nbamvp_analytics_id'

type AnalyticsEvents = {
  page_viewed: { page: 'home' | 'confirmation' }
  prediction_viewed: { season: number; week: number; has_official_results: boolean }
  season_changed: { from_season: number; to_season: number }
  week_changed: { season: number; from_week: number; to_week: number }
  results_toggled: { season: number; week: number; from: boolean; to: boolean }
  more_players_shown: { season: number; week: number; from: number; to: number }
  subscription_requested: Record<string, never>
  confirmation_page_viewed: Record<string, never>
}

let transientAnalyticsId: string | null = null

function createAnalyticsId(): string {
  try {
    if (typeof window.crypto.randomUUID === 'function') return window.crypto.randomUUID()
  } catch {
    // Some browsers expose randomUUID outside a secure context but reject the call.
  }

  const bytes = new Uint8Array(16)
  window.crypto.getRandomValues(bytes)
  bytes[6] = (bytes[6] & 0x0f) | 0x40
  bytes[8] = (bytes[8] & 0x3f) | 0x80
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

export function getAnalyticsId(): string {
  if (transientAnalyticsId) return transientAnalyticsId

  try {
    const stored = window.localStorage.getItem(ANALYTICS_ID_KEY)
    if (stored) {
      transientAnalyticsId = stored
      return stored
    }

    transientAnalyticsId = createAnalyticsId()
    window.localStorage.setItem(ANALYTICS_ID_KEY, transientAnalyticsId)
    return transientAnalyticsId
  } catch {
    transientAnalyticsId = createAnalyticsId()
    return transientAnalyticsId
  }
}

export function track<Event extends keyof AnalyticsEvents>(
  event: Event,
  properties: AnalyticsEvents[Event],
): void {
  if (import.meta.env.DEV && window.location.pathname.startsWith('/preview')) return

  const layout = window.matchMedia('(max-width: 640px)').matches ? 'mobile' : 'desktop'

  void fetch('/api/analytics/events', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      distinct_id: getAnalyticsId(),
      event,
      properties: { ...properties, layout },
    }),
    keepalive: true,
  }).catch(() => undefined)
}
