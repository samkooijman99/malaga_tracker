import { useState, useEffect, useMemo, useRef } from 'react'
import './Analysis.css'

const HISTORY_URL = import.meta.env.BASE_URL + 'data/history.json'

const AIRPORT_COLORS = {
  AMS: '#0d6efd',
  BRU: '#d63384',
  EIN: '#fd7e14',
  RTM: '#20c997',
}

const AIRPORTS = ['AMS', 'BRU', 'EIN', 'RTM']

const priceClass = p =>
  p < 100 ? 'price-cheapest' : p < 250 ? 'price-mid' : 'price-high'

// "2026-04-15" → "15 Apr"
const fmtShort = iso => {
  const d = new Date(iso)
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
}
// "2026-04-15" → "15 Apr 2026"
const fmtLong = iso => {
  const d = new Date(iso)
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

function PriceChart({ snapshots }) {
  const [hoverIdx, setHoverIdx] = useState(null)
  const svgRef = useRef(null)

  const W = 640, H = 260
  const pad = { top: 16, right: 16, bottom: 34, left: 48 }
  const plotW = W - pad.left - pad.right
  const plotH = H - pad.top - pad.bottom

  if (snapshots.length === 0) {
    return <div className="chart-empty">No snapshots yet.</div>
  }
  if (snapshots.length === 1) {
    const s = snapshots[0]
    return (
      <div className="chart-empty single-snapshot">
        <div className={`empty-price ${priceClass(s.cheapest)}`}>
          &euro;{Math.round(s.cheapest)}
        </div>
        <div className="empty-sub">
          Snapshot on {fmtLong(s.date)}. A trend line appears after tomorrow&rsquo;s scrape.
        </div>
      </div>
    )
  }

  const allPrices = snapshots.flatMap(s => [s.cheapest, ...Object.values(s.airports || {})])
  const minP = Math.floor(Math.min(...allPrices) / 10) * 10
  const maxP = Math.ceil(Math.max(...allPrices) / 10) * 10
  const range = Math.max(maxP - minP, 10)

  const xFor = i => pad.left + (i * plotW) / (snapshots.length - 1)
  const yFor = p => pad.top + plotH - ((p - minP) / range) * plotH

  const airportsSeen = Array.from(
    new Set(snapshots.flatMap(s => Object.keys(s.airports || {})))
  ).sort()

  const seriesFor = getter =>
    snapshots.map((s, i) => ({ x: xFor(i), y: yFor(getter(s)), v: getter(s) }))
      .filter(p => Number.isFinite(p.v))

  const cheapestLine = seriesFor(s => s.cheapest)
  const airportLines = airportsSeen.map(ap => ({
    airport: ap,
    points: seriesFor(s => s.airports?.[ap]),
  }))

  const pathFrom = pts => pts.map((p, i) => `${i ? 'L' : 'M'} ${p.x} ${p.y}`).join(' ')

  // Y ticks: 5 evenly spaced
  const yTicks = Array.from({ length: 5 }, (_, i) => minP + (range * i) / 4)

  // X ticks: up to 4 evenly spaced date labels
  const maxTicks = 4
  const xTickIndices = snapshots.length <= maxTicks
    ? snapshots.map((_, i) => i)
    : Array.from({ length: maxTicks }, (_, k) =>
        Math.round((k * (snapshots.length - 1)) / (maxTicks - 1)))

  const onMove = e => {
    const rect = svgRef.current.getBoundingClientRect()
    const relX = ((e.clientX - rect.left) / rect.width) * W
    let best = 0, bestDist = Infinity
    for (let i = 0; i < snapshots.length; i++) {
      const d = Math.abs(xFor(i) - relX)
      if (d < bestDist) { bestDist = d; best = i }
    }
    setHoverIdx(best)
  }

  const hovered = hoverIdx !== null ? snapshots[hoverIdx] : null

  return (
    <div className="chart-wrap">
      {hovered && (
        <div className="chart-tooltip">
          <div className="tt-date">{fmtLong(hovered.date)}</div>
          <div className="tt-row tt-cheapest">
            <span className="tt-swatch dark" />
            <span className="tt-label">Cheapest</span>
            <strong>&euro;{Math.round(hovered.cheapest)}</strong>
          </div>
          {AIRPORTS.map(ap => {
            const p = hovered.airports?.[ap]
            if (p == null) return null
            return (
              <div key={ap} className="tt-row">
                <span className="tt-swatch" style={{ background: AIRPORT_COLORS[ap] }} />
                <span className="tt-label">{ap}</span>
                <strong>&euro;{Math.round(p)}</strong>
              </div>
            )
          })}
        </div>
      )}

      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        className="chart"
        preserveAspectRatio="xMidYMid meet"
        onMouseMove={onMove}
        onMouseLeave={() => setHoverIdx(null)}
      >
        {/* Y grid + labels */}
        {yTicks.map((t, i) => (
          <g key={i}>
            <line x1={pad.left} x2={pad.left + plotW} y1={yFor(t)} y2={yFor(t)} stroke="#e9ecef" />
            <text x={pad.left - 8} y={yFor(t) + 3} textAnchor="end" fontSize="10" fill="#6c757d">
              &euro;{Math.round(t)}
            </text>
          </g>
        ))}

        {/* X labels */}
        {xTickIndices.map(i => (
          <text
            key={i}
            x={xFor(i)}
            y={H - 12}
            textAnchor={i === 0 ? 'start' : i === snapshots.length - 1 ? 'end' : 'middle'}
            fontSize="10"
            fill="#6c757d"
          >
            {fmtShort(snapshots[i].date)}
          </text>
        ))}

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

        {/* Crosshair + highlighted dots */}
        {hovered && (
          <g className="crosshair">
            <line
              x1={xFor(hoverIdx)} x2={xFor(hoverIdx)}
              y1={pad.top} y2={pad.top + plotH}
              stroke="#adb5bd" strokeDasharray="3 3"
            />
            {AIRPORTS.map(ap => {
              const p = hovered.airports?.[ap]
              if (p == null) return null
              return (
                <circle
                  key={ap}
                  cx={xFor(hoverIdx)} cy={yFor(p)} r="4"
                  fill={AIRPORT_COLORS[ap]} stroke="#fff" strokeWidth="1.5"
                />
              )
            })}
            <circle
              cx={xFor(hoverIdx)} cy={yFor(hovered.cheapest)} r="5"
              fill="#212529" stroke="#fff" strokeWidth="1.5"
            />
          </g>
        )}
      </svg>

      {/* Legend */}
      <div className="legend">
        <span className="legend-item"><span className="swatch cheapest-swatch" /> Cheapest</span>
        {airportsSeen.map(ap => (
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
  if (Math.abs(delta) < 0.5) return { text: 'unchanged', cls: '', arrow: '' }
  return {
    text: `${delta > 0 ? '+' : ''}€${Math.round(delta)} (${pct > 0 ? '+' : ''}${pct.toFixed(1)}%)`,
    cls: delta > 0 ? 'up' : 'down',
    arrow: delta > 0 ? '↑' : '↓',
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

  // Lowest price ever seen for this week (across all snapshots)
  const lowest = snapshots.length
    ? snapshots.reduce((best, s) => (!best || s.cheapest < best.cheapest ? s : best), null)
    : null

  // Cheapest airport in the latest snapshot
  const latestBestAirport = latest && latest.airports
    ? Object.entries(latest.airports).sort((a, b) => a[1] - b[1])[0]?.[0]
    : null

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
          <div className="card-label">Latest cheapest</div>
          <div className={`card-value ${latest ? priceClass(latest.cheapest) : ''}`}>
            {latest ? `€${Math.round(latest.cheapest)}` : '—'}
          </div>
          <div className="card-sub">
            {latest ? `via ${latestBestAirport} · ${fmtShort(latest.date)}` : '\u00A0'}
          </div>
        </div>
        <div className="summary-card">
          <div className="card-label">Since first snapshot</div>
          <div className={`card-value ${change?.cls || ''}`}>
            {change ? <>{change.arrow && <span className="arrow">{change.arrow}</span>}{change.text}</> : '—'}
          </div>
          <div className="card-sub">
            {snapshots.length > 1
              ? `${snapshots.length} snapshots`
              : 'Need 2+ snapshots'}
          </div>
        </div>
        <div className="summary-card">
          <div className="card-label">Lowest seen</div>
          <div className={`card-value ${lowest ? priceClass(lowest.cheapest) : ''}`}>
            {lowest ? `€${Math.round(lowest.cheapest)}` : '—'}
          </div>
          <div className="card-sub">
            {lowest ? `on ${fmtShort(lowest.date)}` : '\u00A0'}
          </div>
        </div>
      </div>

      <PriceChart snapshots={snapshots} />

      <table className="history-table">
        <thead>
          <tr>
            <th>Date</th>
            <th className="num">Cheapest</th>
            {AIRPORTS.map(ap => (
              <th key={ap} className="num">{ap}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {[...snapshots].reverse().map(s => {
            const prices = AIRPORTS.map(ap => s.airports?.[ap])
            const minPrice = Math.min(...prices.filter(p => p != null))
            return (
              <tr key={s.date}>
                <td>{fmtShort(s.date)}</td>
                <td className="num"><strong>€{Math.round(s.cheapest)}</strong></td>
                {AIRPORTS.map((ap, i) => {
                  const p = prices[i]
                  const isBest = p != null && p === minPrice
                  return (
                    <td key={ap} className={`num ${isBest ? 'best-cell' : ''}`}>
                      {p != null ? `€${Math.round(p)}` : '—'}
                    </td>
                  )
                })}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
