import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Toaster } from './Toast.tsx'
import { getAnalyticsId, track } from './analytics.ts'
import { toast } from './toast-manager.ts'

export type CountdownInfo = {
  kind: 'first_prediction' | 'next_prediction' | 'next_season'
  target: string
  seasonYear?: number
  seasonLabel?: string
}

export type HomeState = {
  status: 'in_season' | 'awaiting_first_prediction' | 'offseason_results' | 'offseason_waiting_results' | 'no_data'
  seasonYear: number | null
  seasonLabel: string | null
  week: number | null
  countdown: CountdownInfo | null
}

export type Season = {
  year: number
  label: string
  weeks: number[]
  latestWeek: number
  resultsAvailable: boolean
}

export type PredictionRow = {
  rank: number
  rankChange: number | null
  player: string
  team: string
  teamAcronym: string
  teamBackground: string
  teamColor: string
  predictedVotes: number
  gamesPlayed: number
  points: number
  rebounds: number
  assists: number
  trueShooting: number
  winPercentage: number
  actualRank?: number | null
  actualVotes?: number
}

export type PredictionWeek = {
  year: number
  seasonLabel: string
  week: number
  generatedAt: string
  isFinal: boolean
  resultsAvailable: boolean
  previousWeek: number | null
  nextWeek: number | null
  totalRows: number
  hasMore: boolean
  rows: PredictionRow[]
}

type TimeLeft = { months: number; days: number; hours: number; minutes: number; seconds: number }

export type AppDataSource = {
  getHome: () => Promise<HomeState>
  getSeasons: () => Promise<Season[]>
  getPrediction: (year: number, week: number, limit: number) => Promise<PredictionWeek>
}

export type SubscriptionDataSource = {
  subscribe: (email: string, website: string) => Promise<{ message: string }>
}

const httpDataSource: AppDataSource = {
  async getHome() {
    const response = await fetch('/api/home')
    if (!response.ok) throw new Error('Could not load the current season')
    return response.json() as Promise<HomeState>
  },
  async getSeasons() {
    const response = await fetch('/api/seasons')
    if (!response.ok) throw new Error('Could not load the season archive')
    return response.json() as Promise<Season[]>
  },
  async getPrediction(year, week, limit) {
    const response = await fetch(`/api/seasons/${year}/weeks/${week}?limit=${limit}`)
    if (!response.ok) throw new Error('That prediction could not be loaded')
    return response.json() as Promise<PredictionWeek>
  },
}

const httpSubscriptionDataSource: SubscriptionDataSource = {
  async subscribe(email, website) {
    const response = await fetch('/api/subscriptions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, website, analytics_id: getAnalyticsId() }),
    })
    const body = await response.json()
    if (!response.ok) throw new Error(body.detail ?? 'Unable to subscribe right now.')
    return body
  },
}

const dateFormatter = new Intl.DateTimeFormat('en-US', {
  month: 'long',
  day: 'numeric',
  year: 'numeric',
})

const shortDateFormatter = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
})

function parseLocalDate(value: string) {
  return new Date(`${value}T00:00:00`)
}

function getTimeLeft(target: string): TimeLeft {
  const now = new Date()
  const end = parseLocalDate(target)
  if (end <= now) return { months: 0, days: 0, hours: 0, minutes: 0, seconds: 0 }

  let cursor = new Date(now)
  let months = 0
  while (true) {
    const next = new Date(cursor)
    next.setMonth(next.getMonth() + 1)
    if (next > end) break
    cursor = next
    months += 1
  }

  const remainingSeconds = Math.max(0, Math.floor((end.getTime() - cursor.getTime()) / 1000))
  return {
    months,
    days: Math.floor(remainingSeconds / 86400),
    hours: Math.floor((remainingSeconds % 86400) / 3600),
    minutes: Math.floor((remainingSeconds % 3600) / 60),
    seconds: remainingSeconds % 60,
  }
}

function Countdown({ info }: { info: CountdownInfo }) {
  const [timeLeft, setTimeLeft] = useState(() => getTimeLeft(info.target))

  useEffect(() => {
    setTimeLeft(getTimeLeft(info.target))
    const timer = window.setInterval(() => setTimeLeft(getTimeLeft(info.target)), 1000)
    return () => window.clearInterval(timer)
  }, [info.target])

  const title =
    info.kind === 'next_season'
      ? `The ${info.seasonLabel} season starts in`
      : 'The first MVP prediction arrives in'
  const units = ([
    ['month', timeLeft.months],
    ['day', timeLeft.days],
    ['hour', timeLeft.hours],
    ['minute', timeLeft.minutes],
    ['second', timeLeft.seconds],
  ] as const).map(([label, value]) => `${value} ${label}${value === 1 ? '' : 's'}`)

  return <p>{title} {units.join(', ')}.</p>
}

function Arrow({ direction }: { direction: 'left' | 'right' }) {
  return (
    <svg aria-hidden="true" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d={direction === 'left' ? 'm15 18-6-6 6-6' : 'm9 18 6-6-6-6'} />
    </svg>
  )
}

function comparisonClass(row: PredictionRow, showResults: boolean) {
  if (!showResults) return ''
  if (row.rank === 1 && row.actualRank === 1) return 'comparison-mvp'
  if (row.actualRank != null && row.rank === row.actualRank) return 'comparison-exact'
  if (row.actualRank != null && row.rank <= 15) return 'comparison-vote-getter'
  if ((row.rank <= 15 && row.actualRank == null) || (row.rank > 15 && row.actualRank != null)) {
    return 'comparison-miss'
  }
  return ''
}

function RankChange({ value }: { value: number | null }) {
  if (!value) {
    return <span className="rank-change rank-change-none">-</span>
  }

  const direction = value > 0 ? 'up' : 'down'
  const amount = Math.abs(value)
  return (
    <span
      className={`rank-change rank-change-${direction}`}
      aria-label={`Moved ${direction} ${amount} ${amount === 1 ? 'position' : 'positions'}`}
    >
      <span aria-hidden="true">{value > 0 ? '▲' : '▼'} {amount}</span>
    </span>
  )
}

function StatusCopy({ home }: { home: HomeState }) {
  if (home.status === 'in_season' && home.countdown?.kind === 'next_prediction') {
    return (
      <div className="notice">
        <span className="notice-dot bg-emerald-400" />
        <p>Next week&apos;s prediction will be available on {dateFormatter.format(parseLocalDate(home.countdown.target))}.</p>
      </div>
    )
  }
  if (home.status === 'offseason_waiting_results') {
    return (
      <div className="notice-stack">
        <div className="notice">
          <span className="notice-dot bg-emerald-400" />
          <p>The final {home.seasonLabel} prediction is in! Check back soon for official results.</p>
        </div>
        {home.countdown?.kind === 'next_season' && (
          <div className="notice">
            <span className="notice-dot bg-yellow-400" />
            <Countdown info={home.countdown} />
          </div>
        )}
      </div>
    )
  }
  if (home.status === 'offseason_results') {
    return (
      <div className="notice-stack">
        <div className="notice">
          <span className="notice-dot bg-blue-400" />
          <p>The official {home.seasonLabel} results are in! See how our predictions stacked up below.</p>
        </div>
        {home.countdown?.kind === 'next_season' && (
          <div className="notice">
            <span className="notice-dot bg-yellow-400" />
            <Countdown info={home.countdown} />
          </div>
        )}
      </div>
    )
  }
  if (home.status === 'awaiting_first_prediction') {
    return (
      <div className="notice">
        <span className="notice-dot bg-yellow-400" />
        <p>
          The {home.seasonLabel} season has started! The first prediction will be available on{' '}
          {home.countdown?.kind === 'first_prediction'
            ? dateFormatter.format(parseLocalDate(home.countdown.target))
            : 'the first Wednesday after opening week'}.
        </p>
      </div>
    )
  }
  return null
}

function SubscriptionCard({ dataSource }: { dataSource: SubscriptionDataSource }) {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)

  async function subscribe(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    track('subscription_requested', {})
    setLoading(true)
    const form = new FormData(event.currentTarget)
    try {
      const body = await dataSource.subscribe(email, String(form.get('website') ?? ''))
      toast.add({
        id: 'subscription-response',
        type: 'success',
        title: 'Check your email',
        description: body.message,
      })
      setEmail('')
    } catch (reason) {
      toast.add({
        id: 'subscription-response',
        type: 'error',
        title: 'Could not subscribe',
        description: reason instanceof Error ? reason.message : 'Unable to subscribe right now.',
        priority: 'high',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="subscription-card" id="newsletter-subscription">
      <form className="subscribe-form" onSubmit={subscribe}>
        <label className="sr-only" htmlFor="subscription-email">Email address</label>
        <span className="subscription-email-control">
          <input
            id="subscription-email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            autoComplete="email"
            required
          />
          <span className="subscription-email-sizer" aria-hidden="true">
            {`${email} `}
          </span>
        </span>
        <input className="honeypot" type="text" name="website" tabIndex={-1} autoComplete="off" />
        <button className="subscribe-button" type="submit" disabled={loading}>
          {loading ? 'Sending…' : 'Subscribe'}
        </button>
      </form>
    </div>
  )
}

function App({
  dataSource = httpDataSource,
  subscriptionDataSource = httpSubscriptionDataSource,
}: {
  dataSource?: AppDataSource
  subscriptionDataSource?: SubscriptionDataSource
}) {
  const [home, setHome] = useState<HomeState | null>(null)
  const [seasons, setSeasons] = useState<Season[]>([])
  const [selectedYear, setSelectedYear] = useState<number | null>(null)
  const [selectedWeek, setSelectedWeek] = useState<number | null>(null)
  const [prediction, setPrediction] = useState<PredictionWeek | null>(null)
  const [visibleLimit, setVisibleLimit] = useState(30)
  const [showOfficialResults, setShowOfficialResults] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const lastTrackedPrediction = useRef('')

  useEffect(() => {
    Promise.all([dataSource.getHome(), dataSource.getSeasons()])
      .then(([homeData, seasonData]) => {
        setHome(homeData)
        setSeasons(seasonData)
        const params = new URLSearchParams(window.location.search)
        const requestedYear = Number(params.get('season'))
        const requestedWeek = Number(params.get('week'))
        const requestedSeason = seasonData.find((season) => season.year === requestedYear)
        const year = requestedSeason?.year ?? homeData.seasonYear ?? seasonData[0]?.year ?? null
        const season = seasonData.find((item) => item.year === year)
        const week = season?.weeks.includes(requestedWeek)
          ? requestedWeek
          : homeData.seasonYear === year && homeData.week
            ? homeData.week
            : season?.latestWeek ?? null
        setSelectedYear(year)
        setSelectedWeek(week)
      })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false))
  }, [dataSource])

  useEffect(() => {
    if (selectedYear === null || selectedWeek === null) {
      setPrediction(null)
      return
    }
    setLoading(true)
    setError('')
    dataSource.getPrediction(selectedYear, selectedWeek, visibleLimit)
      .then((data) => {
        setPrediction(data)
        const predictionKey = `${data.year}:${data.week}`
        if (predictionKey !== lastTrackedPrediction.current) {
          track('prediction_viewed', {
            season: data.year,
            week: data.week,
            has_official_results: data.resultsAvailable,
          })
          lastTrackedPrediction.current = predictionKey
        }
        const url = new URL(window.location.href)
        url.searchParams.set('season', String(selectedYear))
        url.searchParams.set('week', String(selectedWeek))
        window.history.replaceState({}, '', url)
      })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false))
  }, [dataSource, selectedYear, selectedWeek, visibleLimit])

  const selectedSeason = useMemo(
    () => seasons.find((season) => season.year === selectedYear),
    [seasons, selectedYear],
  )
  const previousSeasonYear = home?.seasonYear == null ? null : home.seasonYear - 1
  const previousSeason = seasons.find((season) => season.year === previousSeasonYear)
  const resultsAvailable = prediction?.isFinal === true && prediction.resultsAvailable
  const showResults = resultsAvailable && showOfficialResults

  function selectSeason(year: number) {
    const season = seasons.find((item) => item.year === year)
    if (selectedYear !== null && selectedYear !== year) {
      track('season_changed', { from_season: selectedYear, to_season: year })
    }
    setVisibleLimit(30)
    setSelectedYear(year)
    setSelectedWeek(season?.latestWeek ?? null)
  }

  function selectWeek(week: number) {
    if (selectedYear !== null && selectedWeek !== null && selectedWeek !== week) {
      track('week_changed', { season: selectedYear, from_week: selectedWeek, to_week: week })
    }
    setVisibleLimit(30)
    setSelectedWeek(week)
  }

  function toggleResults() {
    if (selectedYear !== null && selectedWeek !== null) {
      track('results_toggled', {
        season: selectedYear,
        week: selectedWeek,
        from: showOfficialResults,
        to: !showOfficialResults,
      })
    }
    setShowOfficialResults((current) => !current)
  }

  function showMorePlayers() {
    if (!prediction) return
    const nextLimit = Math.min(visibleLimit + 30, prediction.totalRows)
    track('more_players_shown', {
      season: prediction.year,
      week: prediction.week,
      from: visibleLimit,
      to: nextLimit,
    })
    setVisibleLimit(nextLimit)
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="site-header-inner page-shell">
          <a className="site-brand" href="/" aria-label="NBA MVP Predictor home">
            <span className="logo-mark" aria-hidden="true">🏀</span>
            <p className="site-title">NBA MVP Predictions</p>
          </a>
          <SubscriptionCard dataSource={subscriptionDataSource} />
        </div>
      </header>

      <main>
        {home && home.status !== 'no_data' && (
          <section className="hero-section">
            <div className="page-shell relative py-2">
              <div className={`relative ${home.countdown?.kind === 'next_season' ? '' : 'max-w-3xl'}`}>
                <StatusCopy home={home} />
              </div>
            </div>
          </section>
        )}

        <section className="page-shell pb-7 pt-2 sm:pb-9">
          <div className="season-toolbar">
            <label className="season-select">
              <span className="sr-only">Season</span>
              <span className="season-select-control">
                <select
                  value={selectedYear ?? ''}
                  onChange={(event) => selectSeason(Number(event.target.value))}
                  aria-label="Select season"
                >
                  {seasons.map((season) => (
                    <option value={season.year} key={season.year}>
                      {season.label}
                    </option>
                  ))}
                </select>
                <span className="season-select-value" aria-hidden="true">
                  {selectedSeason ? `${selectedSeason.label} Season` : 'Select season'}
                </span>
              </span>
            </label>
            {resultsAvailable && (
              <button
                type="button"
                className="results-toggle"
                role="switch"
                aria-checked={showOfficialResults}
                onClick={toggleResults}
              >
                <span className="results-toggle-track" aria-hidden="true"><i /></span>
                <span className="results-toggle-label-desktop">Official results</span>
                <span className="results-toggle-label-mobile">Official</span>
              </button>
            )}
            {showResults && (
              <div className="comparison-legend" aria-label="Prediction accuracy legend">
                <span className="legend-item"><i className="legend-swatch comparison-mvp" /> MVP correct</span>
                <span className="legend-item"><i className="legend-swatch comparison-exact" /> Exact rank</span>
                <span className="legend-item"><i className="legend-swatch comparison-vote-getter" /> Close rank</span>
                <span className="legend-item"><i className="legend-swatch comparison-miss" /> Bad miss</span>
              </div>
            )}
          </div>

          {error && <div className="error-card">{error}</div>}

          {!error && home?.status === 'awaiting_first_prediction' && selectedYear === home.seasonYear && !prediction ? (
            previousSeason && (
              <div className="empty-card">
                <a
                  className="text-sm font-semibold text-orange-700 underline underline-offset-4"
                  href={`${window.location.pathname}?season=${previousSeason.year}&week=${previousSeason.latestWeek}`}
                  onClick={(event) => {
                    event.preventDefault()
                    selectSeason(previousSeason.year)
                  }}
                >
                  See last season&apos;s results
                </a>
              </div>
            )
          ) : (
            <div>
              <div className={`table-card ${loading ? 'opacity-60' : ''}`}>
                <div className="table-toolbar">
                  <button
                    className="pager-button"
                    disabled={prediction?.previousWeek == null}
                    onClick={() => prediction?.previousWeek != null && selectWeek(prediction.previousWeek)}
                  >
                    <Arrow direction="left" />
                    <span className="pager-label-desktop">Previous week</span>
                    <span className="pager-label-mobile">Prev</span>
                  </button>
                  {prediction && (
                    <p className="week-summary">
                      {prediction.isFinal ? 'Final week' : `Week ${prediction.week}`} ·{' '}
                      {shortDateFormatter.format(new Date(prediction.generatedAt))}
                    </p>
                  )}
                  <button
                    className="pager-button"
                    disabled={prediction?.nextWeek == null}
                    onClick={() => prediction?.nextWeek != null && selectWeek(prediction.nextWeek)}
                  >
                    <span className="pager-label-desktop">Next week</span>
                    <span className="pager-label-mobile">Next</span>
                    <Arrow direction="right" />
                  </button>
                </div>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th className="rank-column">Rank</th>
                        <th className="rank-change-column">
                          <span className="sr-only">Change</span>
                          <span className="change-heading" aria-hidden="true"><i>▲</i><b>▼</b></span>
                        </th>
                        {showResults && (
                          <th className="rank-column actual-column">Actual</th>
                        )}
                        <th className="player-column">Player</th>
                        <th className="number-column">PTS</th>
                        <th className="number-column">REB</th>
                        <th className="number-column">AST</th>
                        <th className="number-column">GP</th>
                        <th className="number-column">TS%</th>
                        <th className="number-column">Win%</th>
                        <th className="number-column">Predicted votes</th>
                        {showResults && (
                          <th className="number-column actual-column">Actual votes</th>
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {prediction?.rows.map((row) => {
                        return (
                          <tr key={row.player} className={comparisonClass(row, showResults)}>
                            <td className="rank-column">{row.rank}</td>
                            <td className="rank-change-column"><RankChange value={row.rankChange} /></td>
                            {showResults && <td className="rank-column actual-column">{row.actualRank || '-'}</td>}
                            <td className="player-column font-semibold text-slate-950">
                              <span className="player-with-team">
                                <span
                                  className="team-label"
                                  style={{ backgroundColor: row.teamBackground, color: row.teamColor }}
                                  title={row.team}
                                >
                                  {row.teamAcronym}
                                </span>
                                {row.player}
                              </span>
                            </td>
                            <td className="number-column">{row.points.toFixed(1)}</td>
                            <td className="number-column">{row.rebounds.toFixed(1)}</td>
                            <td className="number-column">{row.assists.toFixed(1)}</td>
                            <td className="number-column">{row.gamesPlayed}</td>
                            <td className="number-column">{(row.trueShooting * 100).toFixed(1)}</td>
                            <td className="number-column">{(row.winPercentage * 100).toFixed(1)}</td>
                            <td className="number-column font-semibold text-slate-950">{row.predictedVotes.toLocaleString()}</td>
                            {showResults && (
                              <td className="number-column actual-column font-semibold">{row.actualVotes?.toLocaleString() ?? '—'}</td>
                            )}
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
                {prediction?.hasMore && (
                  <div className="show-more-panel">
                    <button
                      className="show-more-button"
                      disabled={loading}
                      onClick={showMorePlayers}
                    >
                      {loading ? 'Loading…' : 'Show more players'}
                    </button>
                    <span>
                      Showing {prediction.rows.length} of {prediction.totalRows}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

        </section>
      </main>
      <Toaster />
    </div>
  )
}

export default App
