export default function FplPanel({ fplAnalytics }) {
  if (!fplAnalytics || Object.keys(fplAnalytics).length === 0) return null

  const {
    xfpl_per_game, captaincy_score, differential_score, rotation_risk,
    ownership_pct, price, form, points_per_game, total_points,
    ict_index, influence, creativity, threat,
    xGI, starts, goal_pts_value, cs_pts_value,
    transfers_in_event, transfers_out_event,
  } = fplAnalytics

  const net = (transfers_in_event || 0) - (transfers_out_event || 0)
  const rotColor = rotation_risk === 'LOW' ? 'var(--green)'
    : rotation_risk === 'MEDIUM' ? 'var(--amber)' : 'var(--red)'

  return (
    <div style={{
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 16, padding: 24, display: 'flex', flexDirection: 'column', gap: 20
    }}>

      {/* Row 1 — the three headline indexes */}
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
          sub="captain value"
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

      {/* Row 2 — ownership + price + rotation */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        <StatTile label="Ownership" value={`${ownership_pct?.toFixed(1)}%`} sub="selected by" />
        <StatTile label="Price" value={`£${price?.toFixed(1)}m`} sub="FPL value" />
        <StatTile label="Form" value={form?.toFixed(1)} sub="last 4 GW avg" />
        <StatTile
          label="Rotation Risk"
          value={rotation_risk || '—'}
          sub="based on starts"
          valueColor={rotColor}
        />
      </div>

      {/* Divider */}
      <div style={{ borderTop: '1px solid var(--border)' }} />

      {/* ICT Index */}
      <div>
        <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--text-dim)', marginBottom: 12, fontWeight: 600 }}>
          ICT Index
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
          <IctBar label="Overall ICT" value={ict_index} max={400} color="var(--cyan)" />
          <IctBar label="Influence" value={influence} max={800} color="var(--blue)" />
          <IctBar label="Creativity" value={creativity} max={800} color="var(--purple)" />
          <IctBar label="Threat" value={threat} max={800} color="var(--amber)" />
        </div>
      </div>

      {/* Divider */}
      <div style={{ borderTop: '1px solid var(--border)' }} />

      {/* Season stats + scoring rules */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* FPL season stats */}
        <div>
          <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--text-dim)', marginBottom: 12, fontWeight: 600 }}>
            FPL Season
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
            <MiniStat label="Total Points" value={total_points} />
            <MiniStat label="Pts / Game" value={points_per_game?.toFixed(1)} />
            <MiniStat label="xGI" value={xGI?.toFixed(2)} />
            <MiniStat label="Starts" value={starts} />
          </div>
        </div>

        {/* GW transfer intelligence + scoring rules */}
        <div>
          <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--text-dim)', marginBottom: 12, fontWeight: 600 }}>
            This Gameweek
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <TransferRow label="Transfers In" value={transfers_in_event?.toLocaleString()} color="var(--green)" />
            <TransferRow label="Transfers Out" value={transfers_out_event?.toLocaleString()} color="var(--red)" />
            <TransferRow
              label="Net Movement"
              value={(net >= 0 ? '+' : '') + net?.toLocaleString()}
              color={net > 0 ? 'var(--green)' : net < 0 ? 'var(--red)' : 'var(--text-dim)'}
            />
          </div>

          <div style={{ marginTop: 16, fontSize: 11, textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--text-dim)', marginBottom: 8, fontWeight: 600 }}>
            Scoring Rules
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <RuleChip label={`Goal = ${goal_pts_value}pts`} color="var(--green)" />
            <RuleChip label="Assist = 3pts" color="var(--blue)" />
            {cs_pts_value > 0 && <RuleChip label={`Clean Sheet = ${cs_pts_value}pts`} color="var(--cyan)" />}
            <RuleChip label="Yellow = -1pt" color="var(--amber)" />
          </div>
        </div>
      </div>
    </div>
  )
}

function IndexCard({ label, value, unit, sub, color, bar, barColor }) {
  return (
    <div style={{
      background: 'var(--surface-2)', border: '1px solid var(--border)',
      borderRadius: 12, padding: '16px 18px'
    }}>
      <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.8px', color: 'var(--text-dim)', marginBottom: 10, fontWeight: 500 }}>
        {label}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 10 }}>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 28, fontWeight: 700, color }}>
          {value ?? '—'}
        </span>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{unit}</span>
      </div>
      {/* progress bar */}
      <div style={{ height: 4, borderRadius: 2, background: 'var(--surface-3)', overflow: 'hidden', marginBottom: 8 }}>
        <div style={{
          height: '100%', borderRadius: 2,
          width: `${Math.min(100, Math.max(0, bar || 0))}%`,
          background: barColor, transition: 'width 0.8s ease'
        }} />
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{sub}</div>
    </div>
  )
}

function StatTile({ label, value, sub, valueColor }) {
  return (
    <div style={{
      background: 'var(--surface-2)', borderRadius: 10, padding: '12px 14px',
      border: '1px solid var(--border)'
    }}>
      <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 6, fontWeight: 500 }}>{label}</div>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 17, fontWeight: 700, color: valueColor || 'var(--text)' }}>
        {value ?? '—'}
      </div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{sub}</div>
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
        <div style={{
          height: '100%', borderRadius: 3, width: `${pct}%`,
          background: color, transition: 'width 0.8s ease'
        }} />
      </div>
    </div>
  )
}

function MiniStat({ label, value }) {
  return (
    <div style={{
      background: 'var(--surface-3)', borderRadius: 8, padding: '8px 12px',
      display: 'flex', justifyContent: 'space-between', alignItems: 'center'
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
      background: `${color}18`, color, border: `1px solid ${color}30`
    }}>
      {label}
    </div>
  )
}
