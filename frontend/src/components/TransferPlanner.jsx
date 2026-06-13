import { useState, useEffect, useCallback } from 'react'
import PlayerSearch from './PlayerSearch.jsx'
import { comparePlayers } from '../api.js'

const GW_OPTIONS = [1, 3, 5]

// Fixture difficulty colouring based on opponent defence strength.
// Mirrors the backend calibration: min=1000 (easiest) → green, max=1400 (hardest) → red.
function difficultyColor(opp_strength) {
  if (opp_strength == null) return 'var(--text-dim)'
  if (opp_strength < 1100) return 'var(--green)'
  if (opp_strength < 1220) return 'var(--amber)'
  return 'var(--red)'
}

function difficultyLabel(opp_strength) {
  if (opp_strength == null) return ''
  if (opp_strength < 1100) return 'Easy'
  if (opp_strength < 1220) return 'Mid'
  return 'Hard'
}

export default function TransferPlanner({ pendingTransferPlayer, onPendingConsumed }) {
  const [playerOut, setPlayerOut] = useState(null)
  const [playerIn, setPlayerIn]   = useState(null)
  const [gws, setGws]             = useState(3)
  const [hit, setHit]             = useState(0)

  // Accept a player pre-loaded from the Gameweek Planner compare button
  useEffect(() => {
    if (pendingTransferPlayer) {
      setPlayerIn(pendingTransferPlayer)
      onPendingConsumed?.()
    }
  }, [pendingTransferPlayer]) // eslint-disable-line react-hooks/exhaustive-deps

  const [result, setResult]     = useState(null)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState(null)

  const fetch = useCallback(async (pOut, pIn, g, h) => {
    if (!pOut || !pIn) return
    setLoading(true)
    setError(null)
    try {
      const data = await comparePlayers([pOut.id, pIn.id], g, h)
      setResult(data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Comparison failed')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }, [])

  // Auto-fire when players, GW horizon, or hit toggle changes
  useEffect(() => {
    if (playerOut && playerIn) {
      fetch(playerOut, playerIn, gws, hit)
    }
  }, [playerOut, playerIn, gws, hit, fetch])

  const projOut = result?.players?.[0]
  const projIn  = result?.players?.[1]
  const verdict = result?.verdict

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Header */}
      <div>
        <h2 style={{ fontSize: 22, fontWeight: 700, letterSpacing: -0.5, marginBottom: 6 }}>
          Transfer Planner
        </h2>
        <p style={{ fontSize: 13, color: 'var(--text-dim)', maxWidth: 560 }}>
          Compare two players side-by-side. Projections use season-level averages and upcoming
          fixture difficulty — blank gameweeks contribute 0 pts.
        </p>
      </div>

      {/* Controls */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <ControlGroup label="GW Horizon">
          {GW_OPTIONS.map(n => (
            <ToggleBtn key={n} active={gws === n} onClick={() => setGws(n)}>
              {n} GW{n > 1 ? 's' : ''}
            </ToggleBtn>
          ))}
        </ControlGroup>
        <ControlGroup label="Transfer Cost">
          <ToggleBtn active={hit === 0} onClick={() => setHit(0)}>Free</ToggleBtn>
          <ToggleBtn active={hit === 4} onClick={() => setHit(4)}>−4 pts hit</ToggleBtn>
        </ControlGroup>
      </div>

      {/* Player inputs + cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <PlayerSlot
          role="Transfer OUT"
          accentColor="var(--red)"
          accentBg="rgba(239,68,68,0.06)"
          player={playerOut}
          onSelect={setPlayerOut}
          projection={projOut}
          gws={gws}
          loading={loading && !!playerOut}
        />
        <PlayerSlot
          role="Transfer IN"
          accentColor="var(--green)"
          accentBg="rgba(34,197,94,0.06)"
          player={playerIn}
          onSelect={setPlayerIn}
          projection={projIn}
          gws={gws}
          loading={loading && !!playerIn}
        />
      </div>

      {/* Verdict banner */}
      {verdict && !loading && (
        <VerdictBanner verdict={verdict} hit={hit} gws={gws} />
      )}

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

      {/* Empty state */}
      {!playerOut && !playerIn && (
        <div style={{
          textAlign: 'center', padding: '48px 24px',
          color: 'var(--text-dim)', fontSize: 14,
        }}>
          Search for the player you want to transfer out, then the player you want to bring in.
        </div>
      )}
    </div>
  )
}

/* ── PlayerSlot ─────────────────────────────────────────────────────────── */

function PlayerSlot({ role, accentColor, accentBg, player, onSelect, projection, gws, loading }) {
  return (
    <div style={{
      background: 'var(--surface)', border: `1px solid var(--border)`,
      borderRadius: 16, overflow: 'visible',
    }}>
      {/* Slot header */}
      <div style={{
        padding: '14px 16px 10px',
        borderBottom: '1px solid var(--border)',
        background: accentBg,
        borderRadius: '15px 15px 0 0',
      }}>
        <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase',
          letterSpacing: '1px', color: accentColor, marginBottom: 8 }}>
          {role}
        </div>
        <PlayerSearch
          onSelect={onSelect}
          placeholder={`Search ${role === 'Transfer OUT' ? 'player to sell' : 'player to buy'}…`}
        />
      </div>

      {/* Stats + projection (only when player selected) */}
      {player && (
        <div style={{ padding: 16 }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-dim)', fontSize: 13 }}>
              Calculating…
            </div>
          ) : projection ? (
            <>
              <StatsRow projection={projection} accentColor={accentColor} />
              <div style={{ marginTop: 16 }}>
                <SectionLabel>Next {gws} Fixture{gws > 1 ? 's' : ''}</SectionLabel>
                <ProjectionBars projection={projection} accentColor={accentColor} />
              </div>
            </>
          ) : null}
        </div>
      )}
    </div>
  )
}

/* ── StatsRow ────────────────────────────────────────────────────────────── */

function StatsRow({ projection, accentColor }) {
  const rotColor = projection.rotation_risk === 'LOW' ? 'var(--green)'
    : projection.rotation_risk === 'MEDIUM' ? 'var(--amber)' : 'var(--red)'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {/* Projected total — hero number */}
      <div style={{
        background: 'var(--surface-2)', borderRadius: 10, padding: '12px 16px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        border: '1px solid var(--border)',
      }}>
        <div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', fontWeight: 600,
            textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: 4 }}>
            Projected pts
          </div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 28, fontWeight: 700, color: accentColor }}>
            {projection.total_projected.toFixed(1)}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
            range {projection.total_low.toFixed(1)}–{projection.total_high.toFixed(1)}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 6 }}>xFPL / game</div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 18, fontWeight: 700 }}>
            {projection.xfpl_per_game.toFixed(2)}
          </div>
        </div>
      </div>

      {/* Mini stat grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
        <MiniStat label="Pred. Mins" value={projection.predicted_minutes} />
        <MiniStat label="Rotation" value={projection.rotation_risk} valueColor={rotColor} />
        <MiniStat label="Owned" value={`${projection.ownership_pct}%`} />
        <MiniStat label="Price" value={`£${projection.price}m`} />
        <MiniStat label="Form" value={projection.form_index?.toFixed(0)} sub="/ 100" />
        <MiniStat
          label="EO (est.)"
          value={projection.estimated_eo != null ? `${projection.estimated_eo}%` : '—'}
          title="Estimated Effective Ownership. Captaincy portion is approximated — FPL does not publish live captaincy %."
        />
      </div>
      {projection.news && (
        <div style={{
          marginTop: 4, padding: '6px 10px', borderRadius: 7, fontSize: 11,
          background: 'rgba(245,158,11,0.08)', color: 'var(--amber)',
          border: '1px solid rgba(245,158,11,0.2)', lineHeight: 1.4,
        }}>
          {projection.news}
        </div>
      )}
    </div>
  )
}

/* ── ProjectionBars ──────────────────────────────────────────────────────── */

function ProjectionBars({ projection, accentColor }) {
  const maxPts = Math.max(...projection.gw_projections.map(g => g.proj_pts), 1)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {projection.gw_projections.map((gw, i) => (
        <div key={i}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              {gw.blank ? (
                <span style={{ fontSize: 12, color: 'var(--text-muted)', fontStyle: 'italic' }}>
                  Blank GW
                </span>
              ) : (
                <>
                  <span style={{ fontSize: 12, color: difficultyColor(gw.opp_strength),
                    fontWeight: 600, fontFamily: 'var(--mono)' }}>
                    {gw.opponent}
                  </span>
                  <span style={{
                    fontSize: 10, fontWeight: 600, fontFamily: 'var(--mono)',
                    color: difficultyColor(gw.opp_strength),
                    background: `${difficultyColor(gw.opp_strength)}15`,
                    padding: '1px 5px', borderRadius: 4,
                  }}>
                    {gw.home_away} · {difficultyLabel(gw.opp_strength)}
                  </span>
                </>
              )}
            </div>
            {!gw.blank && (
              <span style={{ fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 700,
                color: accentColor }}>
                {gw.proj_pts.toFixed(1)}
              </span>
            )}
          </div>
          {/* Progress bar */}
          <div style={{ height: 5, borderRadius: 3, background: 'var(--surface-3)' }}>
            <div style={{
              height: '100%', borderRadius: 3,
              width: gw.blank ? '0%' : `${Math.min(100, (gw.proj_pts / maxPts) * 100)}%`,
              background: gw.blank ? 'transparent' : accentColor,
              opacity: gw.blank ? 0 : 1,
              transition: 'width 0.6s ease',
            }} />
          </div>
          {!gw.blank && (
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2, textAlign: 'right' }}>
              range {gw.low.toFixed(1)}–{gw.high.toFixed(1)}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

/* ── VerdictBanner ───────────────────────────────────────────────────────── */

function VerdictBanner({ verdict, hit, gws }) {
  const colorMap = {
    TRANSFER: { bg: 'rgba(34,197,94,0.08)', border: 'rgba(34,197,94,0.25)', text: 'var(--green)' },
    MARGINAL:  { bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.25)', text: 'var(--amber)' },
    HOLD:      { bg: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.25)', text: 'var(--red)' },
  }
  const c = colorMap[verdict.recommendation] || colorMap.HOLD
  const deltaSign = verdict.points_delta >= 0 ? '+' : ''

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{
        background: c.bg, border: `1px solid ${c.border}`,
        borderRadius: 14, padding: '20px 24px',
        display: 'flex', alignItems: 'center', gap: 20,
      }}>
        {/* Big delta number */}
        <div style={{ textAlign: 'center', minWidth: 80 }}>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 36, fontWeight: 800, color: c.text, lineHeight: 1 }}>
            {deltaSign}{verdict.points_delta.toFixed(1)}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 4, fontWeight: 600,
            textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            pts over {gws} GW{gws > 1 ? 's' : ''}
          </div>
        </div>

        <div style={{ width: 1, alignSelf: 'stretch', background: c.border }} />

        {/* Verdict text */}
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 16, fontWeight: 700, color: c.text, marginBottom: 4 }}>
            {verdict.recommendation === 'TRANSFER' ? '✓ Make the transfer'
              : verdict.recommendation === 'MARGINAL' ? '⚠ Marginal call'
              : '✕ Hold — not worth it'}
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-dim)', lineHeight: 1.5 }}>
            Range {verdict.points_delta_low > 0 ? '+' : ''}{verdict.points_delta_low.toFixed(1)} to {verdict.points_delta_high > 0 ? '+' : ''}{verdict.points_delta_high.toFixed(1)} pts
            {hit > 0 && (
              <span style={{ marginLeft: 8 }}>
                · <span style={{ color: 'var(--red)' }}>−{hit} hit</span>
                · net {verdict.delta_minus_hit >= 0 ? '+' : ''}{verdict.delta_minus_hit.toFixed(1)} pts
              </span>
            )}
          </div>
        </div>

        {/* Recommendation badge */}
        <div style={{
          padding: '6px 14px', borderRadius: 8, fontFamily: 'var(--mono)',
          fontSize: 12, fontWeight: 700,
          background: c.text + '18', color: c.text, border: `1px solid ${c.border}`,
          whiteSpace: 'nowrap',
        }}>
          {verdict.recommendation}
        </div>
      </div>

      {/* EO / template vs differential note */}
      {verdict.eo_note && (
        <div style={{
          padding: '8px 14px', borderRadius: 9, fontSize: 12,
          background: 'var(--surface-2)', border: '1px solid var(--border)',
          color: 'var(--text-dim)', lineHeight: 1.5,
        }}>
          {verdict.eo_note}
        </div>
      )}
    </div>
  )
}

/* ── Small helpers ───────────────────────────────────────────────────────── */

function SectionLabel({ children }) {
  return (
    <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '1px',
      color: 'var(--text-dim)', marginBottom: 8, fontWeight: 600 }}>
      {children}
    </div>
  )
}

function MiniStat({ label, value, sub, valueColor, title }) {
  return (
    <div title={title} style={{ background: 'var(--surface-2)', borderRadius: 8, padding: '8px 10px',
      border: '1px solid var(--border)', cursor: title ? 'help' : 'default' }}>
      <div style={{ fontSize: 10, color: 'var(--text-dim)', marginBottom: 3, fontWeight: 500 }}>{label}</div>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 13, fontWeight: 700,
        color: valueColor || 'var(--text)' }}>
        {value ?? '—'}{sub && <span style={{ fontSize: 10, color: 'var(--text-muted)' }}> {sub}</span>}
      </div>
    </div>
  )
}

function ControlGroup({ label, children }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <span style={{ fontSize: 12, color: 'var(--text-dim)', fontWeight: 500, whiteSpace: 'nowrap' }}>
        {label}:
      </span>
      <div style={{ display: 'flex', gap: 4 }}>
        {children}
      </div>
    </div>
  )
}

function ToggleBtn({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '5px 12px', borderRadius: 7, cursor: 'pointer',
        fontSize: 12, fontWeight: active ? 600 : 500,
        fontFamily: 'var(--sans)',
        background: active ? 'var(--cyan)' : 'var(--surface-2)',
        color: active ? '#000' : 'var(--text-dim)',
        border: active ? '1px solid var(--cyan)' : '1px solid var(--border)',
        transition: 'all 0.15s',
      }}
    >
      {children}
    </button>
  )
}
