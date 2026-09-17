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

export function getAnalyticsId(): string {
  if (transientAnalyticsId) return transientAnalyticsId

  try {
    const stored = window.localStorage.getItem(ANALYTICS_ID_KEY)
    if (stored) {
      transientAnalyticsId = stored
      return stored
    }

    transientAnalyticsId = window.crypto.randomUUID()
    window.localStorage.setItem(ANALYTICS_ID_KEY, transientAnalyticsId)
    return transientAnalyticsId
  } catch {
    transientAnalyticsId = window.crypto.randomUUID()
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
