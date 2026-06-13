import { useState, useEffect, useMemo } from 'react'
import { getGameweekPlanner } from '../api.js'

const POS_OPTIONS = ['ALL', 'GK', 'DEF', 'MID', 'FWD']

const POS_COLOR = {
  GK:  { bg: 'rgba(245,158,11,0.12)', text: 'var(--amber)' },
  DEF: { bg: 'rgba(34,197,94,0.10)',  text: 'var(--green)' },
  MID: { bg: 'rgba(6,182,212,0.10)',  text: 'var(--cyan)'  },
  FWD: { bg: 'rgba(239,68,68,0.10)',  text: 'var(--red)'   },
}

const ROT_COLOR = { LOW: 'var(--green)', MEDIUM: 'var(--amber)', HIGH: 'var(--red)' }

function diffColor(strength) {
  if (strength == null) return 'var(--text-dim)'
  if (strength < 1100) return 'var(--green)'
  if (strength < 1220) return 'var(--amber)'
  return 'var(--red)'
}

function diffLabel(strength) {
  if (strength == null) return ''
  if (strength < 1100) return 'Easy'
  if (strength < 1220) return 'Mid'
  return 'Hard'
}

const SORT_KEYS = [
  { key: 'proj_pts',            label: 'Proj. Pts' },
  { key: 'xfpl_per_game',       label: 'xFPL' },
  { key: 'fixture_adjusted_form', label: 'Fix. Form' },
  { key: 'form_index',          label: 'Form' },
  { key: 'ownership_pct',       label: 'Own%' },
  { key: 'price',               label: 'Price' },
  { key: 'estimated_eo',        label: 'EO' },
]

export default function GameweekPlanner({ onViewPlayer, onComparePlayer }) {
  const [players, setPlayers]     = useState([])
  const [total, setTotal]         = useState(0)
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState(null)
  const [showAll, setShowAll]     = useState(false)

  // Filters
  const [position, setPosition]       = useState('ALL')
  const [maxPrice, setMaxPrice]       = useState('')
  const [minOwn, setMinOwn]           = useState('')
  const [maxOwn, setMaxOwn]           = useState('')

  // Sort
  const [sortKey, setSortKey]   = useState('proj_pts')
  const [sortAsc, setSortAsc]   = useState(false)

  useEffect(() => {
    setLoading(true)
    setError(null)
    const params = { show_all: showAll }
    if (position !== 'ALL') params.position = position
    if (maxPrice)  params.max_price     = parseFloat(maxPrice)
    if (minOwn)    params.min_ownership = parseFloat(minOwn)
    if (maxOwn)    params.max_ownership = parseFloat(maxOwn)

    getGameweekPlanner(params)
      .then(data => {
        setPlayers(data.players || [])
        setTotal(data.total || 0)
      })
      .catch(e => setError(e.message || 'Failed to load'))
      .finally(() => setLoading(false))
  }, [showAll, position, maxPrice, minOwn, maxOwn])

  const sorted = useMemo(() => {
    const arr = [...players]
    arr.sort((a, b) => {
      const av = a[sortKey] ?? -Infinity
      const bv = b[sortKey] ?? -Infinity
      return sortAsc ? av - bv : bv - av
    })
    return arr
  }, [players, sortKey, sortAsc])

  function toggleSort(key) {
    if (sortKey === key) setSortAsc(v => !v)
    else { setSortKey(key); setSortAsc(false) }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div>
        <h2 style={{ fontSize: 22, fontWeight: 700, letterSpacing: -0.5, marginBottom: 6 }}>
          Gameweek Planner
        </h2>
        <p style={{ fontSize: 13, color: 'var(--text-dim)', maxWidth: 580 }}>
          Ranked by projected GW points. Click a row to view the player report, or use Compare to
          send them to the Transfer Planner.
        </p>
      </div>

      {/* Filters */}
      <div style={{
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 12, padding: '14px 18px',
        display: 'flex', gap: 20, flexWrap: 'wrap', alignItems: 'flex-end',
      }}>
        {/* Position chips */}
        <div>
          <FilterLabel>Position</FilterLabel>
          <div style={{ display: 'flex', gap: 4 }}>
            {POS_OPTIONS.map(p => (
              <button key={p}
                onClick={() => setPosition(p)}
                style={{
                  padding: '4px 10px', borderRadius: 6, cursor: 'pointer',
                  fontSize: 11, fontWeight: 600, fontFamily: 'var(--mono)',
                  background: position === p ? 'var(--cyan)' : 'var(--surface-2)',
                  color: position === p ? '#000' : 'var(--text-dim)',
                  border: position === p ? '1px solid var(--cyan)' : '1px solid var(--border)',
                  transition: 'all 0.12s',
                }}>
                {p}
              </button>
            ))}
          </div>
        </div>

        {/* Max price */}
        <div>
          <FilterLabel>Max Price (£m)</FilterLabel>
          <input
            type="number" min="4" max="16" step="0.5"
            value={maxPrice}
            onChange={e => setMaxPrice(e.target.value)}
            placeholder="Any"
            style={filterInputStyle}
          />
        </div>

        {/* Ownership range */}
        <div>
          <FilterLabel>Min Own%</FilterLabel>
          <input
            type="number" min="0" max="100" step="1"
            value={minOwn}
            onChange={e => setMinOwn(e.target.value)}
            placeholder="0"
            style={filterInputStyle}
          />
        </div>
        <div>
          <FilterLabel>Max Own% (differentials)</FilterLabel>
          <input
            type="number" min="0" max="100" step="1"
            value={maxOwn}
            onChange={e => setMaxOwn(e.target.value)}
            placeholder="100"
            style={filterInputStyle}
          />
        </div>

        {/* Reset */}
        {(position !== 'ALL' || maxPrice || minOwn || maxOwn) && (
          <button
            onClick={() => { setPosition('ALL'); setMaxPrice(''); setMinOwn(''); setMaxOwn('') }}
            style={{
              padding: '4px 12px', borderRadius: 6, cursor: 'pointer',
              fontSize: 11, fontWeight: 600, background: 'transparent',
              color: 'var(--text-dim)', border: '1px solid var(--border)',
            }}>
            Clear filters
          </button>
        )}
      </div>

      {/* Sort bar + count */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 10 }}>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <span style={{ fontSize: 11, color: 'var(--text-dim)', fontWeight: 500 }}>Sort:</span>
          {SORT_KEYS.map(s => (
            <button key={s.key}
              onClick={() => toggleSort(s.key)}
              style={{
                padding: '3px 10px', borderRadius: 6, cursor: 'pointer',
                fontSize: 11, fontWeight: sortKey === s.key ? 700 : 500,
                background: sortKey === s.key ? 'var(--surface-2)' : 'transparent',
                color: sortKey === s.key ? 'var(--cyan)' : 'var(--text-dim)',
                border: sortKey === s.key ? '1px solid var(--border)' : '1px solid transparent',
              }}>
              {s.label}{sortKey === s.key ? (sortAsc ? ' ↑' : ' ↓') : ''}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>
            {loading ? 'Loading…' : `Showing ${sorted.length} of ${total}`}
          </span>
          {!showAll && total > 100 && (
            <button onClick={() => setShowAll(true)} style={{
              padding: '3px 10px', borderRadius: 6, cursor: 'pointer',
              fontSize: 11, fontWeight: 600, background: 'transparent',
              color: 'var(--cyan)', border: '1px solid rgba(6,182,212,0.3)',
            }}>
              Show all {total}
            </button>
          )}
          {showAll && (
            <button onClick={() => setShowAll(false)} style={{
              padding: '3px 10px', borderRadius: 6, cursor: 'pointer',
              fontSize: 11, fontWeight: 600, background: 'transparent',
              color: 'var(--text-dim)', border: '1px solid var(--border)',
            }}>
              Top 100
            </button>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{
          padding: '12px 16px', borderRadius: 10,
          background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)',
          color: 'var(--red)', fontSize: 13,
        }}>
          {error}
        </div>
      )}

      {/* Table */}
      {!error && (
        <div style={{
          background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 12, overflow: 'hidden',
        }}>
          {/* Table header */}
          <div style={headerRowStyle}>
            <ColHead width={28}>#</ColHead>
            <ColHead width={220}>Player</ColHead>
            <ColHead width={42}>Pos</ColHead>
            <ColHead width={54} sortKey="price" currentSort={sortKey} asc={sortAsc} onSort={toggleSort}>£m</ColHead>
            <ColHead width={56} sortKey="ownership_pct" currentSort={sortKey} asc={sortAsc} onSort={toggleSort}>Own%</ColHead>
            <ColHead width={60} sortKey="estimated_eo" currentSort={sortKey} asc={sortAsc} onSort={toggleSort} title="Estimated Effective Ownership (ownership + estimated captaincy %). Captaincy portion is approximated — FPL does not publish live captaincy %.">EO est.</ColHead>
            <ColHead width={58} sortKey="xfpl_per_game" currentSort={sortKey} asc={sortAsc} onSort={toggleSort}>xFPL</ColHead>
            <ColHead width={54} sortKey="form_index" currentSort={sortKey} asc={sortAsc} onSort={toggleSort}>Form</ColHead>
            <ColHead width={64} sortKey="fixture_adjusted_form" currentSort={sortKey} asc={sortAsc} onSort={toggleSort}>Fix.Form</ColHead>
            <ColHead width={120}>Next Fixture</ColHead>
            <ColHead width={56}>Rotation</ColHead>
            <ColHead width={66} sortKey="proj_pts" currentSort={sortKey} asc={sortAsc} onSort={toggleSort}>Proj. Pts</ColHead>
            <ColHead width={100}></ColHead>
          </div>

          {/* Rows */}
          {loading ? (
            Array.from({ length: 8 }, (_, i) => <SkeletonRow key={i} rank={i + 1} />)
          ) : sorted.length === 0 ? (
            <div style={{ padding: '48px 24px', textAlign: 'center', color: 'var(--text-dim)', fontSize: 14 }}>
              No players match the current filters.
            </div>
          ) : (
            sorted.map((p, i) => (
              <PlayerRow
                key={p.id}
                rank={i + 1}
                player={p}
                onView={() => onViewPlayer?.({ id: p.id, name: p.name, team: p.team, position: p.position })}
                onCompare={() => onComparePlayer?.({ id: p.id, name: p.name, team: p.team, position: p.position })}
              />
            ))
          )}
        </div>
      )}

      {/* EO footnote */}
      <div style={{ fontSize: 11, color: 'var(--text-muted)', textAlign: 'right' }}>
        EO = ownership + estimated captaincy%. Captaincy portion is approximated — FPL does not publish live captaincy data.
      </div>
    </div>
  )
}

/* ── PlayerRow ───────────────────────────────────────────────────────────── */

function PlayerRow({ rank, player: p, onView, onCompare }) {
  const posStyle = POS_COLOR[p.position] || { bg: 'var(--surface-2)', text: 'var(--text-dim)' }
  const rotColor = ROT_COLOR[p.rotation_risk] || 'var(--text-dim)'
  const hasNews = p.news && p.news.trim()
  const unavail = p.chance_of_playing !== null && p.chance_of_playing < 100

  return (
    <div
      onClick={onView}
      style={{
        display: 'flex', alignItems: 'center',
        padding: '10px 14px', cursor: 'pointer',
        borderBottom: '1px solid var(--border)',
        transition: 'background 0.1s',
      }}
      onMouseEnter={e => e.currentTarget.style.background = 'var(--surface-2)'}
      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
    >
      {/* Rank */}
      <Cell width={28} mono dimmed>{rank}</Cell>

      {/* Player name + team + news badge */}
      <Cell width={220}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, lineHeight: 1.2 }}>
              {p.name}
              {p.is_most_captained && (
                <span style={{
                  marginLeft: 5, fontSize: 9, fontWeight: 700, fontFamily: 'var(--mono)',
                  color: 'var(--amber)', background: 'rgba(245,158,11,0.12)',
                  padding: '1px 4px', borderRadius: 3, verticalAlign: 'middle',
                }}>
                  C
                </span>
              )}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-dim)', lineHeight: 1 }}>{p.team}</div>
          </div>
          {(hasNews || unavail) && (
            <span title={p.news || `${p.chance_of_playing}% chance of playing`} style={{
              fontSize: 9, fontWeight: 700, fontFamily: 'var(--mono)',
              color: unavail && p.chance_of_playing < 75 ? 'var(--red)' : 'var(--amber)',
              background: unavail && p.chance_of_playing < 75 ? 'rgba(239,68,68,0.12)' : 'rgba(245,158,11,0.12)',
              padding: '1px 5px', borderRadius: 3, cursor: 'help', flexShrink: 0,
            }}>
              {p.chance_of_playing != null && p.chance_of_playing < 100
                ? `${p.chance_of_playing}%`
                : 'NEWS'}
            </span>
          )}
        </div>
      </Cell>

      {/* Position */}
      <Cell width={42}>
        <span style={{
          fontSize: 10, fontWeight: 700, fontFamily: 'var(--mono)',
          color: posStyle.text, background: posStyle.bg,
          padding: '2px 6px', borderRadius: 4,
        }}>
          {p.position}
        </span>
      </Cell>

      {/* Price */}
      <Cell width={54} mono>£{p.price?.toFixed(1)}</Cell>

      {/* Ownership */}
      <Cell width={56} mono>{p.ownership_pct?.toFixed(1)}%</Cell>

      {/* EO */}
      <Cell width={60} mono>
        <span title="Estimated Effective Ownership — captaincy portion is approximated">
          {p.estimated_eo?.toFixed(1)}%
        </span>
      </Cell>

      {/* xFPL */}
      <Cell width={58} mono>{p.xfpl_per_game?.toFixed(2)}</Cell>

      {/* Form Index */}
      <Cell width={54}>
        <span style={{
          fontFamily: 'var(--mono)', fontSize: 12,
          color: p.form_index >= 60 ? 'var(--green)' : p.form_index >= 35 ? 'var(--amber)' : 'var(--text-dim)',
        }}>
          {p.form_index?.toFixed(0)}
        </span>
      </Cell>

      {/* Fixture Adjusted Form */}
      <Cell width={64}>
        <span style={{
          fontFamily: 'var(--mono)', fontSize: 12,
          color: p.fixture_adjusted_form >= 60 ? 'var(--green)'
            : p.fixture_adjusted_form >= 35 ? 'var(--amber)' : 'var(--text-dim)',
        }}>
          {p.fixture_adjusted_form?.toFixed(0)}
        </span>
      </Cell>

      {/* Next fixture */}
      <Cell width={120}>
        {p.next_opponent ? (
          <span style={{ fontFamily: 'var(--mono)', fontSize: 11 }}>
            <span style={{ color: diffColor(p.next_opp_strength), fontWeight: 600 }}>
              {p.next_opponent.length > 10 ? p.next_opponent.substring(0, 10) + '…' : p.next_opponent}
            </span>
            <span style={{
              marginLeft: 4, fontSize: 10,
              color: diffColor(p.next_opp_strength),
              background: `${diffColor(p.next_opp_strength)}15`,
              padding: '1px 4px', borderRadius: 3,
            }}>
              {p.next_home_away} · {diffLabel(p.next_opp_strength)}
            </span>
          </span>
        ) : (
          <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>No fixture</span>
        )}
      </Cell>

      {/* Rotation risk */}
      <Cell width={56}>
        <span style={{
          fontSize: 10, fontWeight: 700, fontFamily: 'var(--mono)',
          color: rotColor, background: `${rotColor}15`,
          padding: '1px 5px', borderRadius: 4,
        }}>
          {p.rotation_risk === 'MEDIUM' ? 'MED' : p.rotation_risk}
        </span>
      </Cell>

      {/* Projected points */}
      <Cell width={66}>
        <span style={{
          fontFamily: 'var(--mono)', fontSize: 15, fontWeight: 700,
          color: p.proj_pts >= 6 ? 'var(--green)' : p.proj_pts >= 4 ? 'var(--cyan)' : 'var(--text)',
        }}>
          {p.proj_pts?.toFixed(1)}
        </span>
      </Cell>

      {/* Actions */}
      <Cell width={100}>
        <div
          style={{ display: 'flex', gap: 4 }}
          onClick={e => e.stopPropagation()}
        >
          <ActionBtn onClick={onView} color="var(--cyan)">View</ActionBtn>
          <ActionBtn onClick={onCompare} color="var(--purple)">Compare</ActionBtn>
        </div>
      </Cell>
    </div>
  )
}

/* ── Skeleton loading row ─────────────────────────────────────────────────── */

function SkeletonRow({ rank }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', padding: '10px 14px',
      borderBottom: '1px solid var(--border)',
    }}>
      <Cell width={28}><Skel w={16} /></Cell>
      <Cell width={220}><div><Skel w={120} /><Skel w={70} h={8} mt={4} /></div></Cell>
      <Cell width={42}><Skel w={30} /></Cell>
      <Cell width={54}><Skel w={32} /></Cell>
      <Cell width={56}><Skel w={36} /></Cell>
      <Cell width={60}><Skel w={40} /></Cell>
      <Cell width={58}><Skel w={32} /></Cell>
      <Cell width={54}><Skel w={28} /></Cell>
      <Cell width={64}><Skel w={32} /></Cell>
      <Cell width={120}><Skel w={90} /></Cell>
      <Cell width={56}><Skel w={34} /></Cell>
      <Cell width={66}><Skel w={28} /></Cell>
      <Cell width={100}><Skel w={80} /></Cell>
    </div>
  )
}

function Skel({ w, h = 12, mt = 0 }) {
  return (
    <div style={{
      width: w, height: h, marginTop: mt, borderRadius: 4,
      background: 'var(--surface-2)', animation: 'pulse 1.5s ease-in-out infinite',
    }} />
  )
}

/* ── Small primitives ────────────────────────────────────────────────────── */

const headerRowStyle = {
  display: 'flex', alignItems: 'center',
  padding: '8px 14px',
  background: 'var(--surface-2)',
  borderBottom: '1px solid var(--border)',
}

function ColHead({ children, width, sortKey, currentSort, asc, onSort, title }) {
  const active = sortKey && currentSort === sortKey
  return (
    <div
      title={title}
      onClick={sortKey ? () => onSort(sortKey) : undefined}
      style={{
        width, minWidth: width, flexShrink: 0,
        fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.6px',
        color: active ? 'var(--cyan)' : 'var(--text-muted)',
        cursor: sortKey ? 'pointer' : 'default',
        userSelect: 'none',
      }}
    >
      {children}{active ? (asc ? ' ↑' : ' ↓') : ''}
    </div>
  )
}

function Cell({ children, width, mono, dimmed }) {
  return (
    <div style={{
      width, minWidth: width, flexShrink: 0,
      fontFamily: mono ? 'var(--mono)' : 'var(--sans)',
      fontSize: mono ? 12 : 13,
      color: dimmed ? 'var(--text-muted)' : 'var(--text)',
    }}>
      {children}
    </div>
  )
}

function FilterLabel({ children }) {
  return (
    <div style={{
      fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px',
      color: 'var(--text-muted)', marginBottom: 6,
    }}>
      {children}
    </div>
  )
}

const filterInputStyle = {
  background: 'var(--surface-2)', border: '1px solid var(--border)',
  borderRadius: 7, padding: '4px 8px', color: 'var(--text)',
  fontFamily: 'var(--mono)', fontSize: 12, width: 72, outline: 'none',
}

function ActionBtn({ children, onClick, color }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '3px 8px', borderRadius: 5, cursor: 'pointer',
        fontSize: 10, fontWeight: 700, fontFamily: 'var(--mono)',
        background: `${color}15`, color, border: `1px solid ${color}30`,
        transition: 'background 0.1s',
      }}
      onMouseEnter={e => e.currentTarget.style.background = `${color}25`}
      onMouseLeave={e => e.currentTarget.style.background = `${color}15`}
    >
      {children}
    </button>
  )
}
