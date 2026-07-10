import { useEffect, useMemo, useState } from 'react'

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

function App() {
  const [home, setHome] = useState<HomeState | null>(null)
  const [seasons, setSeasons] = useState<Season[]>([])
  const [selectedYear, setSelectedYear] = useState<number | null>(null)
  const [selectedWeek, setSelectedWeek] = useState<number | null>(null)
  const [prediction, setPrediction] = useState<PredictionWeek | null>(null)
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
    fetch(`/api/seasons/${selectedYear}/weeks/${selectedWeek}`)
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
  }, [selectedYear, selectedWeek])

  const selectedSeason = useMemo(
    () => seasons.find((season) => season.year === selectedYear),
    [seasons, selectedYear],
  )

  function selectSeason(year: number) {
    const season = seasons.find((item) => item.year === year)
    setSelectedYear(year)
    setSelectedWeek(season?.latestWeek ?? null)
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200/80 bg-white/80 backdrop-blur-xl">
        <div className="page-shell flex h-20 items-center justify-between">
          <a className="flex items-center gap-3" href="/" aria-label="NBA MVP Predictor home">
            <span className="logo-mark">M</span>
            <div>
              <p className="text-sm font-bold tracking-tight text-slate-950 sm:text-base">MVP Predictor</p>
              <p className="hidden text-xs text-slate-500 sm:block">Weekly, data-driven forecasts</p>
            </div>
          </a>
          <span className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 shadow-sm">
            NBA · 2022—present
          </span>
        </div>
      </header>

      <main>
        <section className="hero-section">
          <div className="page-shell relative py-16 sm:py-24">
            <div className="hero-orb hero-orb-one" />
            <div className="hero-orb hero-orb-two" />
            <div className="relative max-w-3xl">
              <p className="eyebrow text-orange-600">The race for the league&apos;s top honor</p>
              <h1 className="mt-5 text-5xl font-bold leading-[0.98] tracking-[-0.055em] text-slate-950 sm:text-7xl">
                Who&apos;s leading the <span className="text-gradient">MVP race?</span>
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
                A machine-learning forecast trained on decades of NBA stats and voting results, updated every week.
              </p>
              {home && <StatusCopy home={home} />}
            </div>
            {home?.countdown && (
              <div className="relative mt-10 max-w-3xl">
                <Countdown info={home.countdown} />
              </div>
            )}
          </div>
        </section>

        <section className="page-shell py-12 sm:py-16">
          <div className="mb-8 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="eyebrow text-orange-600">{prediction?.isFinal ? 'Final forecast' : 'Weekly forecast'}</p>
              <h2 className="mt-2 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl">
                {prediction?.seasonLabel ?? 'MVP predictions'}
              </h2>
              {prediction && (
                <p className="mt-2 text-sm text-slate-500">
                  {prediction.isFinal ? 'Final week' : `Week ${prediction.week}`} · Generated{' '}
                  {shortDateFormatter.format(new Date(prediction.generatedAt))}
                </p>
              )}
            </div>
            <label className="season-select">
              <span>Season</span>
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
            <div className={`table-card ${loading ? 'opacity-60' : ''}`}>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th className="rank-column">Rank</th>
                      <th className="player-column">Player</th>
                      <th>Team</th>
                      <th className="number-column">Predicted votes</th>
                      {prediction?.isFinal && prediction.resultsAvailable && (
                        <>
                          <th className="number-column actual-column">Actual rank</th>
                          <th className="number-column actual-column">Actual votes</th>
                        </>
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
                    {prediction?.rows.map((row) => (
                      <tr key={row.player}>
                        <td className="rank-column"><span className={row.rank <= 3 ? 'top-rank' : ''}>{row.rank}</span></td>
                        <td className="player-column font-semibold text-slate-950">{row.player}</td>
                        <td className="whitespace-nowrap text-slate-500">{row.team}</td>
                        <td className="number-column font-semibold text-slate-950">{row.predictedVotes.toLocaleString()}</td>
                        {prediction.isFinal && prediction.resultsAvailable && (
                          <>
                            <td className="number-column actual-column">{row.actualRank || '—'}</td>
                            <td className="number-column actual-column font-semibold">{row.actualVotes?.toLocaleString() ?? '—'}</td>
                          </>
                        )}
                        <td className="number-column">{row.gamesPlayed}</td>
                        <td className="number-column">{row.points.toFixed(1)}</td>
                        <td className="number-column">{row.rebounds.toFixed(1)}</td>
                        <td className="number-column">{row.assists.toFixed(1)}</td>
                        <td className="number-column">{(row.trueShooting * 100).toFixed(1)}</td>
                        <td className="number-column">{(row.winPercentage * 100).toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50/70 px-4 py-4 sm:px-6">
                <button
                  className="pager-button"
                  disabled={prediction?.previousWeek == null}
                  onClick={() => prediction?.previousWeek != null && setSelectedWeek(prediction.previousWeek)}
                >
                  <Arrow direction="left" /> Previous week
                </button>
                <span className="hidden text-xs font-semibold uppercase tracking-wider text-slate-400 sm:block">
                  Top 30 by predicted votes
                </span>
                <button
                  className="pager-button"
                  disabled={prediction?.nextWeek == null}
                  onClick={() => prediction?.nextWeek != null && setSelectedWeek(prediction.nextWeek)}
                >
                  Next week <Arrow direction="right" />
                </button>
              </div>
            </div>
          )}

          {selectedSeason?.resultsAvailable && prediction && !prediction.isFinal && (
            <p className="mt-5 text-center text-sm text-slate-500">
              Navigate to the final week to compare this season&apos;s prediction with the official results.
            </p>
          )}
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="page-shell flex flex-col gap-2 py-8 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <p>Built from weekly NBA stats and historical MVP voting.</p>
          <p>Predictions are for fun, not betting advice.</p>
        </div>
      </footer>
    </div>
  )
}

export default App
