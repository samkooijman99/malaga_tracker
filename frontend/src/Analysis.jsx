import { useState, useEffect, useMemo } from 'react'
import './Analysis.css'

const HISTORY_URL = import.meta.env.BASE_URL + 'data/history.json'

const AIRPORT_COLORS = {
  AMS: '#0d6efd',
  BRU: '#d63384',
  EIN: '#fd7e14',
  RTM: '#20c997',
}

function PriceChart({ snapshots }) {
  const W = 640, H = 260
  const pad = { top: 16, right: 16, bottom: 36, left: 46 }
  const plotW = W - pad.left - pad.right
  const plotH = H - pad.top - pad.bottom

  if (snapshots.length === 0) {
    return <div className="chart-empty">No snapshots yet.</div>
  }

  const allPrices = snapshots.flatMap(s => [s.cheapest, ...Object.values(s.airports || {})])
  const minP = Math.floor(Math.min(...allPrices) / 10) * 10
  const maxP = Math.ceil(Math.max(...allPrices) / 10) * 10
  const range = Math.max(maxP - minP, 10)

  const xFor = i => pad.left + (snapshots.length === 1 ? plotW / 2 : (i * plotW) / (snapshots.length - 1))
  const yFor = p => pad.top + plotH - ((p - minP) / range) * plotH

  const airports = Array.from(
    new Set(snapshots.flatMap(s => Object.keys(s.airports || {})))
  ).sort()

  const seriesFor = (getter) =>
    snapshots.map((s, i) => ({ x: xFor(i), y: yFor(getter(s)), v: getter(s), date: s.date }))
      .filter(p => Number.isFinite(p.v))

  const cheapestLine = seriesFor(s => s.cheapest)
  const airportLines = airports.map(ap => ({
    airport: ap,
    points: seriesFor(s => s.airports?.[ap]),
  }))

  const pathFrom = pts => pts.map((p, i) => `${i ? 'L' : 'M'} ${p.x} ${p.y}`).join(' ')

  // Y ticks: 5 evenly spaced
  const yTicks = Array.from({ length: 5 }, (_, i) => minP + (range * i) / 4)

  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} className="chart" preserveAspectRatio="xMidYMid meet">
        {/* Y grid + labels */}
        {yTicks.map((t, i) => (
          <g key={i}>
            <line x1={pad.left} x2={pad.left + plotW} y1={yFor(t)} y2={yFor(t)} stroke="#e9ecef" />
            <text x={pad.left - 6} y={yFor(t) + 3} textAnchor="end" fontSize="10" fill="#6c757d">
              €{Math.round(t)}
            </text>
          </g>
        ))}

        {/* X labels — first + last snapshot date */}
        <text x={pad.left} y={H - 14} textAnchor="start" fontSize="10" fill="#6c757d">
          {snapshots[0].date}
        </text>
        {snapshots.length > 1 && (
          <text x={pad.left + plotW} y={H - 14} textAnchor="end" fontSize="10" fill="#6c757d">
            {snapshots[snapshots.length - 1].date}
          </text>
        )}

        {/* Per-airport thin lines */}
        {airportLines.map(({ airport, points }) =>
          points.length > 1 ? (
            <path
              key={airport}
              d={pathFrom(points)}
              stroke={AIRPORT_COLORS[airport] || '#adb5bd'}
              strokeWidth="1.5"
              strokeOpacity="0.55"
              fill="none"
            />
          ) : null
        )}

        {/* Cheapest line (bold, dark) */}
        {cheapestLine.length > 1 && (
          <path d={pathFrom(cheapestLine)} stroke="#212529" strokeWidth="2.5" fill="none" />
        )}

        {/* Cheapest dots + title tooltips */}
        {cheapestLine.map((p, i) => (
          <g key={i}>
            <circle cx={p.x} cy={p.y} r="3.5" fill="#212529" />
            <title>{p.date}: €{Math.round(p.v)} (cheapest)</title>
          </g>
        ))}
      </svg>

      {/* Legend */}
      <div className="legend">
        <span className="legend-item"><span className="swatch cheapest-swatch" /> Cheapest</span>
        {airports.map(ap => (
          <span key={ap} className="legend-item">
            <span className="swatch" style={{ background: AIRPORT_COLORS[ap] || '#adb5bd' }} />
            {ap}
          </span>
        ))}
      </div>
    </div>
  )
}

function formatChange(snapshots) {
  if (snapshots.length < 2) return null
  const first = snapshots[0].cheapest
  const last = snapshots[snapshots.length - 1].cheapest
  const delta = last - first
  const pct = (delta / first) * 100
  if (Math.abs(delta) < 0.5) return { text: 'unchanged', cls: '' }
  return {
    text: `${delta > 0 ? '+' : ''}€${Math.round(delta)} (${pct > 0 ? '+' : ''}${pct.toFixed(1)}%)`,
    cls: delta > 0 ? 'up' : 'down',
  }
}

export default function Analysis() {
  const [history, setHistory] = useState(null)
  const [error, setError] = useState(null)
  const [selectedWed, setSelectedWed] = useState(null)

  useEffect(() => {
    fetch(HISTORY_URL, { cache: 'no-cache' })
      .then(r => { if (!r.ok) throw new Error(r.statusText); return r.json() })
      .then(setHistory)
      .catch(setError)
  }, [])

  const weeksList = useMemo(() => {
    if (!history?.weeks) return []
    return Object.values(history.weeks).sort((a, b) => a.wednesday.localeCompare(b.wednesday))
  }, [history])

  useEffect(() => {
    if (!selectedWed && weeksList.length) setSelectedWed(weeksList[0].wednesday)
  }, [weeksList, selectedWed])

  if (error) return <div className="state-msg">Could not load history.<br /><span className="muted">{error.message}</span></div>
  if (!history) return <div className="state-msg">Loading history...</div>

  if (weeksList.length === 0) {
    return (
      <div className="state-msg">
        <p><strong>No history yet.</strong></p>
        <p className="muted">
          The scraper appends a snapshot each day. Come back tomorrow for the
          first trend line.
        </p>
      </div>
    )
  }

  const week = weeksList.find(w => w.wednesday === selectedWed) || weeksList[0]
  const snapshots = week.snapshots || []
  const latest = snapshots[snapshots.length - 1]
  const change = formatChange(snapshots)

  return (
    <div className="analysis">
      <div className="analysis-controls">
        <label>
          <span className="label-text">Week</span>
          <select value={selectedWed} onChange={e => setSelectedWed(e.target.value)}>
            {weeksList.map(w => (
              <option key={w.wednesday} value={w.wednesday}>{w.label}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="analysis-summary">
        <div className="summary-card">
          <div className="card-label">Snapshots</div>
          <div className="card-value">{snapshots.length}</div>
        </div>
        <div className="summary-card">
          <div className="card-label">Latest cheapest</div>
          <div className="card-value">
            {latest ? `€${Math.round(latest.cheapest)}` : '—'}
          </div>
        </div>
        <div className="summary-card">
          <div className="card-label">Since first snapshot</div>
          <div className={`card-value ${change?.cls || ''}`}>
            {change?.text || '—'}
          </div>
        </div>
      </div>

      <PriceChart snapshots={snapshots} />

      <table className="history-table">
        <thead>
          <tr>
            <th>Date</th>
            <th className="num">Cheapest</th>
            <th className="num">AMS</th>
            <th className="num">BRU</th>
            <th className="num">EIN</th>
            <th className="num">RTM</th>
          </tr>
        </thead>
        <tbody>
          {[...snapshots].reverse().map(s => (
            <tr key={s.date}>
              <td>{s.date}</td>
              <td className="num"><strong>€{Math.round(s.cheapest)}</strong></td>
              {['AMS', 'BRU', 'EIN', 'RTM'].map(ap => (
                <td key={ap} className="num">
                  {s.airports?.[ap] != null ? `€${Math.round(s.airports[ap])}` : '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
