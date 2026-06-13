export default function FplPanel({ fplAnalytics }) {
  if (!fplAnalytics || Object.keys(fplAnalytics).length === 0) return null

  const {
    xfpl_per_game, captaincy_score, differential_score,
    form_index, fixture_adjusted_form,
    rotation_risk, ownership_pct, estimated_eo, is_most_captained,
    price, form, points_per_game, total_points,
    ict_index, influence, creativity, threat,
    xGI, starts, sub_appearances, predicted_minutes,
    goal_pts_value, cs_pts_value,
    transfers_in_event, transfers_out_event,
    xg_last3, xg_last5, xg_last10,
    xa_last3, xa_last5, xgi_last5,
    news, chance_of_playing_next_round,
  } = fplAnalytics

  const net = (transfers_in_event || 0) - (transfers_out_event || 0)
  const rotColor = rotation_risk === 'LOW' ? 'var(--green)'
    : rotation_risk === 'MEDIUM' ? 'var(--amber)' : 'var(--red)'
  const fafDelta = fixture_adjusted_form != null && form_index != null
    ? (fixture_adjusted_form - form_index).toFixed(1) : null

  return (
    <div style={{
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 16, padding: 24, display: 'flex', flexDirection: 'column', gap: 20,
    }}>

      {/* ── Row 1: Three headline indexes ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
        <IndexCard
          label="xFPL / Game"
          value={xfpl_per_game?.toFixed(2)}
          unit="pts"
          sub="expected fantasy pts"
          color="var(--cyan)"
          bar={Math.min(100, (xfpl_per_game / 15) * 100)}
          barColor="var(--cyan)"
        />
        <IndexCard
          label="Captaincy Score"
          value={captaincy_score?.toFixed(0)}
          unit="/ 100"
          sub="2× points as captain"
          color={captaincy_score >= 60 ? 'var(--green)' : captaincy_score >= 35 ? 'var(--amber)' : 'var(--text-dim)'}
          bar={captaincy_score}
          barColor={captaincy_score >= 60 ? 'var(--green)' : 'var(--amber)'}
        />
        <IndexCard
          label="Differential"
          value={differential_score?.toFixed(0)}
          unit="/ 100"
          sub="low-owned upside"
          color={differential_score >= 50 ? 'var(--purple)' : 'var(--text-dim)'}
          bar={differential_score}
          barColor="var(--purple)"
        />
      </div>

      {/* ── Row 2: Form indexes ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
        <IndexCard
          label="Form Index"
          value={form_index?.toFixed(1)}
          unit="/ 100"
          sub="xG · xA · SOT · KeyPass · Mins"
          color={form_index >= 60 ? 'var(--green)' : form_index >= 35 ? 'var(--amber)' : 'var(--text-dim)'}
          bar={form_index}
          barColor={form_index >= 60 ? 'var(--green)' : 'var(--amber)'}
        />
        <IndexCard
          label="Fixture Adjusted Form"
          value={fixture_adjusted_form?.toFixed(1)}
          unit="/ 100"
          sub={fafDelta != null
            ? `${fafDelta > 0 ? '+' : ''}${fafDelta} vs raw form · vs opponent defence`
            : 'vs opponent defence strength'}
          color={fixture_adjusted_form >= 60 ? 'var(--green)' : fixture_adjusted_form >= 35 ? 'var(--amber)' : 'var(--text-dim)'}
          bar={fixture_adjusted_form}
          barColor={fixture_adjusted_form >= form_index ? 'var(--green)' : 'var(--red)'}
        />
      </div>

      <div style={{ borderTop: '1px solid var(--border)' }} />

      {/* ── FPL News / Availability ── */}
      {(news || (chance_of_playing_next_round != null && chance_of_playing_next_round < 100)) && (
        <div style={{
          padding: '10px 14px', borderRadius: 10, fontSize: 12, lineHeight: 1.5,
          background: chance_of_playing_next_round != null && chance_of_playing_next_round < 75
            ? 'rgba(239,68,68,0.07)' : 'rgba(245,158,11,0.07)',
          border: `1px solid ${chance_of_playing_next_round != null && chance_of_playing_next_round < 75
            ? 'rgba(239,68,68,0.2)' : 'rgba(245,158,11,0.2)'}`,
          color: chance_of_playing_next_round != null && chance_of_playing_next_round < 75
            ? 'var(--red)' : 'var(--amber)',
          display: 'flex', gap: 10, alignItems: 'flex-start',
        }}>
          <span style={{ fontFamily: 'var(--mono)', fontWeight: 700, flexShrink: 0 }}>
            {chance_of_playing_next_round != null ? `${chance_of_playing_next_round}%` : 'NEWS'}
          </span>
          <span>{news || `${chance_of_playing_next_round}% chance of playing next round`}</span>
        </div>
      )}

      {/* ── Row 3: Availability ── */}
      <div>
        <SectionLabel>Availability & Rotation</SectionLabel>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 10 }}>
          <StatTile
            label="Ownership"
            value={`${ownership_pct?.toFixed(1)}%`}
            sub="selected by"
          />
          <StatTile
            label="EO (estimated)"
            value={estimated_eo != null ? `${estimated_eo}%` : '—'}
            sub={is_most_captained ? 'most captained this GW' : 'ownership + cap. est.'}
            tooltip="Estimated Effective Ownership. Captaincy portion approximated — FPL does not publish live captaincy %."
          />
          <StatTile label="Price" value={`£${price?.toFixed(1)}m`} sub="FPL value" />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
          <StatTile label="Starts" value={starts} sub={`${sub_appearances} sub apps`} />
          <StatTile label="Pred. Minutes" value={predicted_minutes} sub="per game" />
          <StatTile label="Rotation Risk" value={rotation_risk || '—'} sub="from starts data" valueColor={rotColor} />
        </div>
      </div>

      <div style={{ borderTop: '1px solid var(--border)' }} />

      {/* ── Row 4: Rolling windows ── */}
      <div>
        <SectionLabel>Rolling Form Windows</SectionLabel>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
          {/* xG windows */}
          <WindowCard label="xG Windows">
            <WindowRow name="Last 3" value={xg_last3} color="var(--cyan)" max={3} />
            <WindowRow name="Last 5" value={xg_last5} color="var(--cyan)" max={5} />
            <WindowRow name="Last 10" value={xg_last10} color="var(--cyan)" max={8} />
          </WindowCard>

          {/* xA windows */}
          <WindowCard label="xA Windows (assists proxy)">
            <WindowRow name="Last 3" value={xa_last3} color="var(--blue)" max={3} />
            <WindowRow name="Last 5" value={xa_last5} color="var(--blue)" max={4} />
          </WindowCard>

          {/* xGI window */}
          <WindowCard label="xGI Last 5 (G+A)">
            <WindowRow name="xGI Last 5" value={xgi_last5} color="var(--purple)" max={6} />
            <WindowRow name="FPL Season xGI" value={xGI?.toFixed(2)} color="var(--purple)" max={20} numericMax={20} />
          </WindowCard>
        </div>
      </div>

      <div style={{ borderTop: '1px solid var(--border)' }} />

      {/* ── Row 5: ICT Index ── */}
      <div>
        <SectionLabel>ICT Index</SectionLabel>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
          <IctBar label="Overall ICT" value={ict_index} max={400} color="var(--cyan)" />
          <IctBar label="Influence"   value={influence}  max={800} color="var(--blue)" />
          <IctBar label="Creativity"  value={creativity} max={800} color="var(--purple)" />
          <IctBar label="Threat"      value={threat}     max={800} color="var(--amber)" />
        </div>
      </div>

      <div style={{ borderTop: '1px solid var(--border)' }} />

      {/* ── Row 6: Season stats + GW transfers + scoring rules ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        <div>
          <SectionLabel>FPL Season</SectionLabel>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
            <MiniStat label="Total Pts"  value={total_points} />
            <MiniStat label="Pts/Game"   value={points_per_game?.toFixed(1)} />
            <MiniStat label="FPL Form"   value={form?.toFixed(1)} />
            <MiniStat label="Season xGI" value={xGI?.toFixed(2)} />
          </div>
        </div>

        <div>
          <SectionLabel>This Gameweek</SectionLabel>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 14 }}>
            <TransferRow label="Transfers In"  value={(transfers_in_event || 0).toLocaleString()}  color="var(--green)" />
            <TransferRow label="Transfers Out" value={(transfers_out_event || 0).toLocaleString()} color="var(--red)" />
            <TransferRow
              label="Net Movement"
              value={(net >= 0 ? '+' : '') + net.toLocaleString()}
              color={net > 0 ? 'var(--green)' : net < 0 ? 'var(--red)' : 'var(--text-dim)'}
            />
          </div>
          <SectionLabel>Scoring Rules</SectionLabel>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <RuleChip label={`Goal = ${goal_pts_value}pts`}    color="var(--green)" />
            <RuleChip label="Assist = 3pts"                     color="var(--blue)" />
            {cs_pts_value > 0 && <RuleChip label={`Clean Sheet = ${cs_pts_value}pts`} color="var(--cyan)" />}
            <RuleChip label="Yellow = −1pt"  color="var(--amber)" />
            <RuleChip label="Red = −3pts"    color="var(--red)" />
          </div>
        </div>
      </div>

    </div>
  )
}

/* ── Sub-components ─────────────────────────────────────────────────────── */

function SectionLabel({ children }) {
  return (
    <div style={{
      fontSize: 11, textTransform: 'uppercase', letterSpacing: '1px',
      color: 'var(--text-dim)', marginBottom: 12, fontWeight: 600,
    }}>
      {children}
    </div>
  )
}

function IndexCard({ label, value, unit, sub, color, bar, barColor }) {
  return (
    <div style={{
      background: 'var(--surface-2)', border: '1px solid var(--border)',
      borderRadius: 12, padding: '16px 18px',
    }}>
      <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.8px', color: 'var(--text-dim)', marginBottom: 10, fontWeight: 500 }}>
        {label}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 10 }}>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 26, fontWeight: 700, color }}>
          {value ?? '—'}
        </span>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{unit}</span>
      </div>
      <div style={{ height: 4, borderRadius: 2, background: 'var(--surface-3)', overflow: 'hidden', marginBottom: 8 }}>
        <div style={{
          height: '100%', borderRadius: 2,
          width: `${Math.min(100, Math.max(0, bar || 0))}%`,
          background: barColor, transition: 'width 0.8s ease',
        }} />
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{sub}</div>
    </div>
  )
}

function StatTile({ label, value, sub, valueColor, tooltip }) {
  return (
    <div title={tooltip} style={{
      background: 'var(--surface-2)', borderRadius: 10, padding: '12px 14px',
      border: '1px solid var(--border)', cursor: tooltip ? 'help' : 'default',
    }}>
      <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 6, fontWeight: 500 }}>{label}</div>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 17, fontWeight: 700, color: valueColor || 'var(--text)' }}>
        {value ?? '—'}
      </div>
      {sub && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{sub}</div>}
    </div>
  )
}

function WindowCard({ label, children }) {
  return (
    <div style={{
      background: 'var(--surface-2)', border: '1px solid var(--border)',
      borderRadius: 10, padding: '12px 14px',
    }}>
      <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 10, fontWeight: 500 }}>{label}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>{children}</div>
    </div>
  )
}

function WindowRow({ name, value, color, max, numericMax }) {
  const numVal = typeof value === 'string' ? parseFloat(value) : (value || 0)
  const effectiveMax = numericMax || max
  const pct = Math.min(100, (numVal / effectiveMax) * 100)
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>{name}</span>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 600, color }}>{value ?? '—'}</span>
      </div>
      <div style={{ height: 4, borderRadius: 2, background: 'var(--surface-3)' }}>
        <div style={{ height: '100%', borderRadius: 2, width: `${pct}%`, background: color, transition: 'width 0.6s ease' }} />
      </div>
    </div>
  )
}

function IctBar({ label, value, max, color }) {
  const pct = Math.min(100, ((value || 0) / max) * 100)
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
        <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>{label}</span>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 12, fontWeight: 600, color }}>{value?.toFixed(0) ?? '—'}</span>
      </div>
      <div style={{ height: 5, borderRadius: 3, background: 'var(--surface-3)' }}>
        <div style={{ height: '100%', borderRadius: 3, width: `${pct}%`, background: color, transition: 'width 0.8s ease' }} />
      </div>
    </div>
  )
}

function MiniStat({ label, value }) {
  return (
    <div style={{
      background: 'var(--surface-3)', borderRadius: 8, padding: '8px 12px',
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    }}>
      <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>{label}</span>
      <span style={{ fontFamily: 'var(--mono)', fontSize: 13, fontWeight: 600 }}>{value ?? '—'}</span>
    </div>
  )
}

function TransferRow({ label, value, color }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>{label}</span>
      <span style={{ fontFamily: 'var(--mono)', fontSize: 13, fontWeight: 600, color }}>{value}</span>
    </div>
  )
}

function RuleChip({ label, color }) {
  return (
    <div style={{
      fontSize: 11, fontFamily: 'var(--mono)', fontWeight: 600,
      padding: '3px 8px', borderRadius: 6,
      background: `${color}18`, color, border: `1px solid ${color}30`,
    }}>
      {label}
    </div>
  )
}
