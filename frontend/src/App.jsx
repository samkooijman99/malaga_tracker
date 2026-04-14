import { useState, useEffect } from 'react'
import WeekSection from './components/WeekSection.jsx'
import './App.css'

const DATA_URL = import.meta.env.BASE_URL + 'data/flights.json'

export default function App() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('ALL')
  const [refreshing, setRefreshing] = useState(false)

  const loadData = (bustCache = false) => {
    setRefreshing(true)
    setError(null)
    const url = bustCache ? `${DATA_URL}?t=${Date.now()}` : DATA_URL
    fetch(url, { cache: 'reload' })
      .then(r => { if (!r.ok) throw new Error(r.statusText); return r.json() })
      .then(d => { setData(d); setRefreshing(false) })
      .catch(e => { setError(e); setRefreshing(false) })
  }

  useEffect(() => { loadData() }, [])

  if (error) return (
    <div className="state-msg">
      <p>Could not load flight data.</p>
      <p className="muted">{error.message}</p>
    </div>
  )

  if (!data) return <div className="state-msg">Loading flights...</div>

  const airports = ['ALL', 'AMS', 'BRU', 'EIN', 'RTM']
  const updatedAt = data.generated_at
    ? new Date(data.generated_at).toLocaleDateString('en-GB', {
        day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit'
      })
    : 'never'

  const allDeals = data.weeks.flatMap(w => w.deals)
  const globalCheapest = allDeals.length
    ? Math.min(...allDeals.map(d => d.price_eur))
    : null

  const progress = data.progress  // {completed, total} when a run is in progress

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-inner">
          <h1>Malaga Flight Tracker</h1>
          <p className="subtitle">AMS / BRU / EIN / RTM &rarr; AGP &nbsp;&bull;&nbsp; Wed/Thu out, Sun return</p>
          {globalCheapest && (
            <p className="global-cheapest">
              Cheapest in 6 months: <strong>&euro;{Math.round(globalCheapest)}</strong>
            </p>
          )}
          <p className="updated">
            Updated {updatedAt}
            {progress && progress.completed < progress.total && (
              <span className="progress-chip">
                &nbsp;• scraping {progress.completed}/{progress.total} weeks
              </span>
            )}
            <button
              type="button"
              className="refresh-btn"
              onClick={() => loadData(true)}
              disabled={refreshing}
              title="Fetch latest flights.json (bypasses cache)"
            >
              {refreshing ? 'Refreshing...' : '↻ Refresh'}
            </button>
          </p>
        </div>
      </header>

      <div className="filter-bar">
        {airports.map(ap => (
          <button
            key={ap}
            className={filter === ap ? 'active' : ''}
            onClick={() => setFilter(ap)}
          >
            {ap}
          </button>
        ))}
      </div>

      <main className="main">
        {data.weeks.length === 0 ? (
          <div className="state-msg">
            <p><strong>No flight data yet.</strong></p>
            <p className="muted">
              The first scrape is running on the server. Come back in ~25&nbsp;min
              (or whenever the cron finishes) and refresh.
            </p>
          </div>
        ) : (
          data.weeks.map((weekData, i) => {
            const deals = filter === 'ALL'
              ? weekData.deals
              : weekData.deals.filter(d => d.origin_iata === filter)
            if (!deals.length) return null
            return (
              <WeekSection
                key={i}
                week={weekData.week}
                deals={deals}
              />
            )
          })
        )}
      </main>
    </div>
  )
}
