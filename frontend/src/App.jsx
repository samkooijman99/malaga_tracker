import { useState, useEffect } from 'react'
import WeekSection from './components/WeekSection.jsx'
import Analysis from './Analysis.jsx'
import './App.css'

const DATA_URL = import.meta.env.BASE_URL + 'data/flights.json'

// "11:05 AM" or "4:05 PM" → 11.08 or 16.08 (24h decimal)
function parseHour(s) {
  if (!s) return null
  const m = s.match(/(\d{1,2}):(\d{2})\s*(AM|PM)/i)
  if (!m) return null
  let h = parseInt(m[1], 10)
  const min = parseInt(m[2], 10)
  const pm = m[3].toUpperCase() === 'PM'
  if (pm && h !== 12) h += 12
  if (!pm && h === 12) h = 0
  return h + min / 60
}

export default function App() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('ALL')
  const [eveningOnly, setEveningOnly] = useState(false)
  const [view, setView] = useState('main')  // 'main' | 'analysis'

  useEffect(() => {
    fetch(DATA_URL, { cache: 'no-cache' })
      .then(r => { if (!r.ok) throw new Error(r.statusText); return r.json() })
      .then(setData)
      .catch(setError)
  }, [])

  if (error) return (
    <div className="state-msg">
      <p>Could not load flight data.</p>
      <p className="muted">{error.message}</p>
    </div>
  )

  if (!data) return <div className="state-msg">Loading flights...</div>

  const airports = ['ALL', 'AMS', 'BRU', 'EIN', 'RTM']
  const updatedAt = data.generated_at
    ? new Date(data.generated_at).toLocaleString('en-GB', {
        day: 'numeric', month: 'long', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
        timeZone: 'Europe/Amsterdam',
      }) + ' CET'
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
          <div className="header-top">
            <h1>Malaga Flight Tracker</h1>
            <nav className="nav">
              <button
                className={view === 'main' ? 'active' : ''}
                onClick={() => setView('main')}
              >Deals</button>
              <button
                className={view === 'analysis' ? 'active' : ''}
                onClick={() => setView('analysis')}
              >Analysis</button>
            </nav>
          </div>
          <p className="subtitle">AMS / BRU / EIN / RTM &rarr; AGP &nbsp;&bull;&nbsp; Wed/Thu out, Sun return</p>
          {view === 'main' && globalCheapest && (
            <p className="global-cheapest">
              Cheapest in 6 months:{' '}
              <strong className={
                globalCheapest < 100 ? 'price-cheapest'
                : globalCheapest < 250 ? 'price-mid'
                : 'price-high'
              }>&euro;{Math.round(globalCheapest)}</strong>
            </p>
          )}
          <p className="updated">
            Updated {updatedAt}
            {progress && progress.completed < progress.total && (
              <span className="progress-chip">
                &nbsp;• scraping {progress.completed}/{progress.total} weeks
              </span>
            )}
          </p>
        </div>
      </header>

      {view === 'main' && (
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
          <button
            className={`time-filter ${eveningOnly ? 'active' : ''}`}
            onClick={() => setEveningOnly(v => !v)}
            title="Only show deals whose outbound flight departs at or after 17:00"
          >
            {eveningOnly ? '✓ ' : ''}Evening only dep (17:00+)
          </button>
        </div>
      )}

      <main className="main">
        {view === 'analysis' ? (
          <Analysis />
        ) : data.weeks.length === 0 ? (
          <div className="state-msg">
            <p><strong>No flight data yet.</strong></p>
            <p className="muted">
              The first scrape is running on the server. Come back in ~25&nbsp;min
              (or whenever the cron finishes) and refresh.
            </p>
          </div>
        ) : (
          data.weeks.map((weekData, i) => {
            let deals = filter === 'ALL'
              ? weekData.deals
              : weekData.deals.filter(d => d.origin_iata === filter)
            if (eveningOnly) {
              deals = deals.filter(d => {
                const h = parseHour(d.outbound_dep)
                return h !== null && h >= 17
              })
            }
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
