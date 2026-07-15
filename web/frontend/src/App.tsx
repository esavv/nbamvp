import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'

type CountdownInfo = {
  kind: 'first_prediction' | 'next_season'
  target: string
  seasonYear?: number
  seasonLabel?: string
}

type HomeState = {
  status: 'in_season' | 'awaiting_first_prediction' | 'offseason_results' | 'offseason_waiting_results' | 'no_data'
  seasonYear: number | null
  seasonLabel: string | null
  week: number | null
  countdown: CountdownInfo | null
}

type Season = {
  year: number
  label: string
  weeks: number[]
  latestWeek: number
  resultsAvailable: boolean
}

type PredictionRow = {
  rank: number
  rankChange: number | null
  player: string
  team: string
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

type PredictionWeek = {
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

type TimeLeft = { months: number; days: number; hours: number; seconds: number }

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
  if (end <= now) return { months: 0, days: 0, hours: 0, seconds: 0 }

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

  return (
    <section className="countdown-card" aria-label={title}>
      <div>
        <p className="eyebrow text-amber-300">{info.kind === 'next_season' ? 'Next tip-off' : 'Opening week'}</p>
        <h2 className="mt-2 text-2xl font-semibold text-white sm:text-3xl">{title}</h2>
        <p className="mt-2 text-sm text-slate-300">{dateFormatter.format(parseLocalDate(info.target))}</p>
      </div>
      <div className="mt-7 grid grid-cols-4 gap-2 sm:gap-4">
        {([
          ['months', timeLeft.months],
          ['days', timeLeft.days],
          ['hours', timeLeft.hours],
          ['seconds', timeLeft.seconds],
        ] as const).map(([label, value]) => (
          <div className="countdown-unit" key={label}>
            <span className="tabular-nums">{String(value).padStart(2, '0')}</span>
            <small>{label}</small>
          </div>
        ))}
      </div>
    </section>
  )
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
  if (home.status === 'offseason_waiting_results') {
    return (
      <div className="notice">
        <span className="notice-dot bg-amber-400" />
        <p>
          The final {home.seasonLabel} prediction is in. Official MVP results aren&apos;t available here yet.
        </p>
      </div>
    )
  }
  if (home.status === 'offseason_results') {
    return (
      <div className="notice">
        <span className="notice-dot bg-emerald-400" />
        <p>The official results are in. See how the final {home.seasonLabel} prediction performed.</p>
      </div>
    )
  }
  if (home.status === 'awaiting_first_prediction') {
    return (
      <div className="notice">
        <span className="notice-dot bg-orange-500" />
        <p>The {home.seasonLabel} season has started. The model needs one week of games before its first prediction.</p>
      </div>
    )
  }
  return null
}

function SubscriptionCard() {
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [confirmationToken, setConfirmationToken] = useState(
    () => new URLSearchParams(window.location.search).get('subscription_token') ?? '',
  )

  useEffect(() => {
    if (confirmationToken) {
      document.getElementById('newsletter-subscription')?.scrollIntoView({ block: 'center' })
    }
  }, [confirmationToken])

  async function subscribe(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setMessage('')
    const form = new FormData(event.currentTarget)
    try {
      const response = await fetch('/api/subscriptions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, website: form.get('website') ?? '' }),
      })
      const body = await response.json()
      if (!response.ok) throw new Error(body.detail ?? 'Unable to subscribe right now.')
      setMessage(body.message)
      setEmail('')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to subscribe right now.')
    } finally {
      setLoading(false)
    }
  }

  async function confirmSubscription() {
    setLoading(true)
    setError('')
    try {
      const response = await fetch('/api/subscriptions/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: confirmationToken }),
      })
      const body = await response.json()
      if (!response.ok) throw new Error(body.detail ?? 'Unable to confirm this subscription.')
      setMessage(body.message)
      setConfirmationToken('')
      const url = new URL(window.location.href)
      url.searchParams.delete('subscription_token')
      window.history.replaceState({}, '', url)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to confirm this subscription.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="subscription-card" id="newsletter-subscription">
      <div className="subscription-copy">
        <h2>{confirmationToken ? 'Confirm your subscription' : 'Get predictions in your inbox'}</h2>
        <p>
          {confirmationToken
            ? 'Confirm below to receive NBA MVP predictions during the season.'
            : 'One weekly email during the season, no spam.'}
        </p>
      </div>
      {confirmationToken ? (
        <button className="subscribe-button" disabled={loading} onClick={confirmSubscription}>
          {loading ? 'Confirming…' : 'Confirm subscription'}
        </button>
      ) : (
        <form className="subscribe-form" onSubmit={subscribe}>
          <label className="sr-only" htmlFor="subscription-email">Email address</label>
          <input
            id="subscription-email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            autoComplete="email"
            required
          />
          <input className="honeypot" type="text" name="website" tabIndex={-1} autoComplete="off" />
          <button className="subscribe-button" type="submit" disabled={loading}>
            {loading ? 'Sending…' : 'Subscribe'}
          </button>
        </form>
      )}
      {(message || error) && (
        <div className="subscription-response" aria-live="polite">
          {message && <p className="text-emerald-700">{message}</p>}
          {error && <p className="text-red-700">{error}</p>}
          <button
            className="subscription-response-dismiss"
            type="button"
            aria-label="Dismiss subscription message"
            onClick={() => {
              setMessage('')
              setError('')
            }}
          >
            ×
          </button>
        </div>
      )}
    </div>
  )
}

function App() {
  const [home, setHome] = useState<HomeState | null>(null)
  const [seasons, setSeasons] = useState<Season[]>([])
  const [selectedYear, setSelectedYear] = useState<number | null>(null)
  const [selectedWeek, setSelectedWeek] = useState<number | null>(null)
  const [prediction, setPrediction] = useState<PredictionWeek | null>(null)
  const [visibleLimit, setVisibleLimit] = useState(30)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      fetch('/api/home').then((response) => {
        if (!response.ok) throw new Error('Could not load the current season')
        return response.json() as Promise<HomeState>
      }),
      fetch('/api/seasons').then((response) => {
        if (!response.ok) throw new Error('Could not load the season archive')
        return response.json() as Promise<Season[]>
      }),
    ])
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
  }, [])

  useEffect(() => {
    if (selectedYear === null || selectedWeek === null) {
      setPrediction(null)
      return
    }
    setLoading(true)
    setError('')
    fetch(`/api/seasons/${selectedYear}/weeks/${selectedWeek}?limit=${visibleLimit}`)
      .then((response) => {
        if (!response.ok) throw new Error('That prediction could not be loaded')
        return response.json() as Promise<PredictionWeek>
      })
      .then((data) => {
        setPrediction(data)
        const url = new URL(window.location.href)
        url.searchParams.set('season', String(selectedYear))
        url.searchParams.set('week', String(selectedWeek))
        window.history.replaceState({}, '', url)
      })
      .catch((reason: Error) => setError(reason.message))
      .finally(() => setLoading(false))
  }, [selectedYear, selectedWeek, visibleLimit])

  const selectedSeason = useMemo(
    () => seasons.find((season) => season.year === selectedYear),
    [seasons, selectedYear],
  )

  function selectSeason(year: number) {
    const season = seasons.find((item) => item.year === year)
    setVisibleLimit(30)
    setSelectedYear(year)
    setSelectedWeek(season?.latestWeek ?? null)
  }

  function selectWeek(week: number) {
    setVisibleLimit(30)
    setSelectedWeek(week)
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200/80 bg-white/80 backdrop-blur-xl">
        <div className="site-header-inner page-shell">
          <a className="flex items-center gap-3" href="/" aria-label="NBA MVP Predictor home">
            <span className="logo-mark" aria-hidden="true">🏀</span>
            <div>
              <p className="text-sm font-bold tracking-tight text-slate-950 sm:text-base">NBA MVP Predictions</p>
            </div>
          </a>
          <SubscriptionCard />
        </div>
      </header>

      <main>
        <section className="hero-section">
          <div className="page-shell relative pb-2 pt-[14px]">
            <div className="hero-orb hero-orb-one" />
            <div className="hero-orb hero-orb-two" />
            <div className="relative max-w-3xl">
              <h1 className="text-3xl font-bold leading-tight tracking-[-0.04em] text-slate-950 sm:text-5xl">
                Who&apos;s leading the <span className="text-gradient">NBA MVP race?</span>
              </h1>
              {home && <StatusCopy home={home} />}
            </div>
            {home?.countdown && (
              <div className="relative mt-6 max-w-3xl">
                <Countdown info={home.countdown} />
              </div>
            )}
          </div>
        </section>

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
          </div>

          {error && <div className="error-card">{error}</div>}

          {!error && home?.status === 'awaiting_first_prediction' && selectedYear === home.seasonYear && !prediction ? (
            <div className="empty-card">
              <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-orange-100 text-2xl">🏀</div>
              <h3 className="text-xl font-bold text-slate-950">The model is warming up</h3>
              <p className="mx-auto mt-2 max-w-md text-slate-500">
                Check back after the first full week of games for this season&apos;s opening prediction.
              </p>
            </div>
          ) : (
            <div>
              {prediction?.isFinal && prediction.resultsAvailable && (
                <div className="comparison-legend" aria-label="Prediction accuracy legend">
                  <span className="legend-item"><i className="legend-swatch comparison-mvp" /> MVP correct</span>
                  <span className="legend-item"><i className="legend-swatch comparison-exact" /> Correct rank</span>
                  <span className="legend-item"><i className="legend-swatch comparison-vote-getter" /> Close rank</span>
                  <span className="legend-item"><i className="legend-swatch comparison-miss" /> Top-15 miss</span>
                </div>
              )}
              <div className={`table-card ${loading ? 'opacity-60' : ''}`}>
                <div className="table-toolbar">
                  <button
                    className="pager-button"
                    disabled={prediction?.previousWeek == null}
                    onClick={() => prediction?.previousWeek != null && selectWeek(prediction.previousWeek)}
                  >
                    <Arrow direction="left" />
                    <span className="pager-label-desktop">Previous week</span>
                    <span className="pager-label-mobile">Prev.<br />week</span>
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
                    <span className="pager-label-mobile">Next<br />week</span>
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
                        {prediction?.isFinal && prediction.resultsAvailable && (
                          <th className="rank-column actual-column">Actual rank</th>
                        )}
                        <th className="player-column">Player</th>
                        <th>Team</th>
                        <th className="number-column">Predicted votes</th>
                        {prediction?.isFinal && prediction.resultsAvailable && (
                          <th className="number-column actual-column">Actual votes</th>
                        )}
                        <th className="number-column">GP</th>
                        <th className="number-column">PTS</th>
                        <th className="number-column">REB</th>
                        <th className="number-column">AST</th>
                        <th className="number-column">TS%</th>
                        <th className="number-column">Win%</th>
                      </tr>
                    </thead>
                    <tbody>
                      {prediction?.rows.map((row) => {
                        const showResults = prediction.isFinal && prediction.resultsAvailable
                        return (
                          <tr key={row.player} className={comparisonClass(row, showResults)}>
                            <td className="rank-column"><span className={row.rank <= 3 ? 'top-rank' : ''}>{row.rank}</span></td>
                            <td className="rank-change-column"><RankChange value={row.rankChange} /></td>
                            {showResults && <td className="rank-column actual-column">{row.actualRank || '—'}</td>}
                            <td className="player-column font-semibold text-slate-950">{row.player}</td>
                            <td className="whitespace-nowrap text-slate-500">{row.team}</td>
                            <td className="number-column font-semibold text-slate-950">{row.predictedVotes.toLocaleString()}</td>
                            {showResults && (
                              <td className="number-column actual-column font-semibold">{row.actualVotes?.toLocaleString() ?? '—'}</td>
                            )}
                            <td className="number-column">{row.gamesPlayed}</td>
                            <td className="number-column">{row.points.toFixed(1)}</td>
                            <td className="number-column">{row.rebounds.toFixed(1)}</td>
                            <td className="number-column">{row.assists.toFixed(1)}</td>
                            <td className="number-column">{(row.trueShooting * 100).toFixed(1)}</td>
                            <td className="number-column">{(row.winPercentage * 100).toFixed(1)}</td>
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
                      onClick={() => setVisibleLimit((current) => Math.min(current + 30, prediction.totalRows))}
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

      <footer className="border-t border-slate-200 bg-white">
        <div className="page-shell py-8 text-sm text-slate-500">
          <p>A machine-learning forecast trained on decades of NBA stats and voting results, updated every week.</p>
        </div>
      </footer>
    </div>
  )
}

export default App
