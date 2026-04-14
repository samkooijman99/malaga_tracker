import { useState } from 'react'
import './WeekSection.css'

function StopsBadge({ stops }) {
  if (stops === 0) return <span className="badge direct">direct</span>
  return <span className="badge stops">{stops} stop{stops > 1 ? 's' : ''}</span>
}

// "11:05 AM on Wed, Apr 15" → "11:05 AM"
function shortTime(s) {
  if (!s) return ''
  const i = s.indexOf(' on ')
  return i >= 0 ? s.slice(0, i) : s
}

function priceClass(price) {
  if (price < 100) return 'price-cheapest'  // green
  if (price < 250) return 'price-mid'       // orange
  return 'price-high'                        // red
}

export default function WeekSection({ week, deals }) {
  const [expanded, setExpanded] = useState(false)
  const cheapest = deals[0]?.price_eur ?? Infinity

  return (
    <section className="week-section">
      <div
        className="week-header"
        onClick={() => setExpanded(e => !e)}
        role="button"
        tabIndex={0}
        onKeyDown={e => e.key === 'Enter' && setExpanded(v => !v)}
      >
        <div className="week-title">
          <span className="week-label">{week.label}</span>
          <span className="week-dates">
            {week.wednesday} / {week.thursday} &rarr; {week.sunday}
          </span>
        </div>
        <div className="week-summary">
          <span className="from">from </span>
          <span className={`week-best-price ${priceClass(cheapest)}`}>&euro;{Math.round(cheapest)}</span>
          <span className="chevron">{expanded ? '▲' : '▼'}</span>
        </div>
      </div>

      {expanded && (
        <div className="week-body">
          <table>
            <thead>
              <tr>
                <th>Airport</th>
                <th>Day</th>
                <th>Outbound</th>
                <th>Airline</th>
                <th>Return</th>
                <th>Airline</th>
                <th className="price-col">Price</th>
              </tr>
            </thead>
            <tbody>
              {deals.map((deal, i) => (
                <tr key={i} className={deal.price_eur === cheapest ? 'row-cheapest' : ''}>
                  <td data-label="Airport">
                    <span className="iata">{deal.origin_iata}</span>
                    <span className="airport-name">{deal.origin_name}</span>
                  </td>
                  <td data-label="Day">{deal.outbound_day.slice(0, 3)}</td>
                  <td className="time-cell" data-label="Outbound">
                    {shortTime(deal.outbound_dep)}&thinsp;&rarr;&thinsp;{shortTime(deal.outbound_arr)}
                    <StopsBadge stops={deal.outbound_stops} />
                  </td>
                  <td data-label="Airline">{deal.outbound_airline}</td>
                  <td className="time-cell" data-label="Return">
                    {shortTime(deal.return_dep)}&thinsp;&rarr;&thinsp;{shortTime(deal.return_arr)}
                    <StopsBadge stops={deal.return_stops} />
                    {deal.return_iata && deal.return_iata !== deal.origin_iata && (
                      <span className="return-airport" title={`Lands at ${deal.return_name}`}>
                        to <strong>{deal.return_iata}</strong>
                      </span>
                    )}
                  </td>
                  <td data-label="Airline">{deal.return_airline}</td>
                  <td data-label="Price" className={`price-col ${priceClass(deal.price_eur)}`}>
                    &euro;{Math.round(deal.price_eur)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
