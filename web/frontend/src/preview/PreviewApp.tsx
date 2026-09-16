import { useState } from 'react'
import App from '../App.tsx'
import type { AppDataSource, HomeState, PredictionRow, PredictionWeek, Season } from '../App.tsx'

type Scenario = {
  label: string
  home: HomeState
  seasons: Season[]
  predictions: PredictionWeek[]
}

const predictionRows: PredictionRow[] = [
  { rank: 1, rankChange: 0, player: 'Nikola Jokic', team: 'DEN', predictedVotes: 892, gamesPlayed: 70, points: 29.6, rebounds: 12.7, assists: 10.2, trueShooting: 0.671, winPercentage: 0.659, actualRank: 1, actualVotes: 926 },
  { rank: 2, rankChange: 1, player: 'Shai Gilgeous-Alexander', team: 'OKC', predictedVotes: 731, gamesPlayed: 72, points: 31.4, rebounds: 5.1, assists: 6.4, trueShooting: 0.642, winPercentage: 0.817, actualRank: 2, actualVotes: 739 },
  { rank: 3, rankChange: -1, player: 'Luka Doncic', team: 'LAL', predictedVotes: 486, gamesPlayed: 66, points: 28.8, rebounds: 8.4, assists: 8.1, trueShooting: 0.612, winPercentage: 0.598, actualRank: 5, actualVotes: 311 },
  { rank: 4, rankChange: 2, player: 'Giannis Antetokounmpo', team: 'MIL', predictedVotes: 352, gamesPlayed: 68, points: 30.3, rebounds: 11.9, assists: 6.5, trueShooting: 0.658, winPercentage: 0.573, actualRank: 3, actualVotes: 470 },
  { rank: 5, rankChange: -1, player: 'Jayson Tatum', team: 'BOS', predictedVotes: 218, gamesPlayed: 74, points: 27.1, rebounds: 8.6, assists: 5.4, trueShooting: 0.604, winPercentage: 0.744, actualRank: 5, actualVotes: 172 },
  { rank: 6, rankChange: 0, player: 'Anthony Edwards', team: 'MIN', predictedVotes: 129, gamesPlayed: 76, points: 27.6, rebounds: 5.8, assists: 4.7, trueShooting: 0.591, winPercentage: 0.622 },
]

function futureDate(days: number) {
  const date = new Date()
  date.setHours(12, 0, 0, 0)
  date.setDate(date.getDate() + days)
  return date.toISOString().slice(0, 10)
}

function prediction(week: number, resultsAvailable: boolean): PredictionWeek {
  return {
    year: 2026,
    seasonLabel: '2025–26',
    week,
    generatedAt: week === 24 ? '2026-04-08T09:00:00' : '2026-04-15T09:00:00',
    isFinal: week === 25,
    resultsAvailable,
    previousWeek: week === 25 ? 24 : null,
    nextWeek: week === 24 ? 25 : null,
    totalRows: predictionRows.length,
    hasMore: false,
    rows: predictionRows,
  }
}

function archivedSeason(resultsAvailable: boolean): Season {
  return {
    year: 2026,
    label: '2025–26',
    weeks: [24, 25],
    latestWeek: 25,
    resultsAvailable,
  }
}

function offseasonHome(
  status: 'offseason_results' | 'offseason_waiting_results',
  countdown: HomeState['countdown'] = null,
): HomeState {
  return {
    status,
    seasonYear: 2026,
    seasonLabel: '2025–26',
    week: 25,
    countdown,
  }
}

const scenarios = {
  awaitingFirstPrediction: {
    label: 'Season start, awaiting first prediction',
    home: {
      status: 'awaiting_first_prediction',
      seasonYear: 2027,
      seasonLabel: '2026–27',
      week: null,
      countdown: { kind: 'first_prediction', target: futureDate(7), seasonYear: 2027, seasonLabel: '2026–27' },
    },
    seasons: [archivedSeason(true)],
    predictions: [prediction(24, true), prediction(25, true)],
  },
  inSeason: {
    label: 'In season',
    home: { status: 'in_season', seasonYear: 2026, seasonLabel: '2025–26', week: 24, countdown: null },
    seasons: [archivedSeason(false)],
    predictions: [prediction(24, false), prediction(25, false)],
  },
  waitingResults: {
    label: 'Off season, awaiting results',
    home: offseasonHome('offseason_waiting_results'),
    seasons: [archivedSeason(false)],
    predictions: [prediction(24, false), prediction(25, false)],
  },
  waitingResultsCountdown: {
    label: 'Off season, awaiting results, next season announced',
    home: offseasonHome('offseason_waiting_results', {
      kind: 'next_season',
      target: futureDate(45),
      seasonYear: 2027,
      seasonLabel: '2026–27',
    }),
    seasons: [archivedSeason(false)],
    predictions: [prediction(24, false), prediction(25, false)],
  },
  results: {
    label: 'Off season, results available',
    home: offseasonHome('offseason_results'),
    seasons: [archivedSeason(true)],
    predictions: [prediction(24, true), prediction(25, true)],
  },
  resultsCountdown: {
    label: 'Off season, results available, next season announced',
    home: offseasonHome('offseason_results', {
      kind: 'next_season',
      target: futureDate(45),
      seasonYear: 2027,
      seasonLabel: '2026–27',
    }),
    seasons: [archivedSeason(true)],
    predictions: [prediction(24, true), prediction(25, true)],
  },
  noData: {
    label: 'No data',
    home: { status: 'no_data', seasonYear: null, seasonLabel: null, week: null, countdown: null },
    seasons: [],
    predictions: [],
  },
} satisfies Record<string, Scenario>

type ScenarioName = keyof typeof scenarios

function isScenarioName(value: string | null): value is ScenarioName {
  return value !== null && Object.hasOwn(scenarios, value)
}

function dataSourceFor(scenario: Scenario): AppDataSource {
  return {
    async getHome() {
      return scenario.home
    },
    async getSeasons() {
      return scenario.seasons
    },
    async getPrediction(year, week, limit) {
      const match = scenario.predictions.find((item) => item.year === year && item.week === week)
      if (!match) throw new Error('That prediction could not be loaded')
      const rows = match.rows.slice(0, limit)
      return { ...match, rows, hasMore: rows.length < match.totalRows }
    },
  }
}

function initialScenario(): ScenarioName {
  const requested = new URLSearchParams(window.location.search).get('scenario')
  return isScenarioName(requested) ? requested : 'awaitingFirstPrediction'
}

function PreviewApp() {
  const [scenarioName, setScenarioName] = useState<ScenarioName>(initialScenario)
  const scenario = scenarios[scenarioName]

  function selectScenario(nextScenario: ScenarioName) {
    const url = new URL(window.location.href)
    url.searchParams.set('scenario', nextScenario)
    url.searchParams.delete('season')
    url.searchParams.delete('week')
    window.history.replaceState({}, '', url)
    setScenarioName(nextScenario)
  }

  return (
    <>
      <aside
        style={{
          position: 'fixed',
          zIndex: 100,
          right: '16px',
          bottom: '16px',
          width: 'min(360px, calc(100vw - 32px))',
          padding: '12px',
          border: '1px solid #cbd5e1',
          borderRadius: '12px',
          background: '#ffffff',
          boxShadow: '0 12px 32px rgb(15 23 42 / 18%)',
        }}
      >
        <label style={{ display: 'grid', gap: '6px', color: '#0f172a', fontSize: '13px', fontWeight: 700 }}>
          Preview state
          <select
            value={scenarioName}
            onChange={(event) => {
              if (isScenarioName(event.target.value)) selectScenario(event.target.value)
            }}
            style={{ width: '100%', padding: '8px', border: '1px solid #94a3b8', borderRadius: '8px', background: '#ffffff' }}
          >
            {Object.entries(scenarios).map(([name, item]) => (
              <option key={name} value={name}>{item.label}</option>
            ))}
          </select>
        </label>
      </aside>
      <App key={scenarioName} dataSource={dataSourceFor(scenario)} />
    </>
  )
}

export default PreviewApp
