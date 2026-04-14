import { useState } from 'react'
import './WeekSection.css'

function StopsBadge({ stops }) {
  if (stops === 0) return <span className="badge direct">direct</span>
  return <span className="badge stops">{stops} stop{stops > 1 ? 's' : ''}</span>
}

function priceClass(price, cheapest) {
  const ratio = price / cheapest
  if (ratio <= 1.05) return 'price-cheapest'
  if (ratio <= 1.25) return 'price-mid'
  return 'price-high'
}

export default function WeekSection({ week, deals }) {
  const [expanded, setExpanded] = useState(true)
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
          <span className="week-best-price">&euro;{Math.round(cheapest)}</span>
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
                    {deal.outbound_dep}&thinsp;&rarr;&thinsp;{deal.outbound_arr}
                    <StopsBadge stops={deal.outbound_stops} />
                  </td>
                  <td data-label="Airline">{deal.outbound_airline}</td>
                  <td className="time-cell" data-label="Return">
                    {deal.return_dep}&thinsp;&rarr;&thinsp;{deal.return_arr}
                    <StopsBadge stops={deal.return_stops} />
                  </td>
                  <td data-label="Airline">{deal.return_airline}</td>
                  <td data-label="Price" className={`price-col ${priceClass(deal.price_eur, cheapest)}`}>
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
