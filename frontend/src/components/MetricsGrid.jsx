function Metric({ label, value, sub, color = 'var(--text)' }) {
  return (
    <div style={{
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 12, padding: '16px 18px'
    }}>
      <div style={{
        fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.8px',
        color: 'var(--text-dim)', marginBottom: 8, fontWeight: 500
      }}>
        {label}
      </div>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 26, fontWeight: 700, color }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4 }}>
          {sub}
        </div>
      )}
    </div>
  )
}

export default function MetricsGrid({ stats, matchLogs = [] }) {
  if (!stats) return null

  const s = Array.isArray(stats) ? stats[0] : stats
  if (!s) return null

  const goals = s.goals ?? 0
  const apps = s.appearances ?? 0
  const minutes = s.minutes ?? 1
  const shots = s.shots ?? 0
  const xg = s.xG ?? 0
  const sot = s.shots_on_target ?? 0

  const goals90 = minutes > 0 ? ((goals / minutes) * 90).toFixed(2) : '0.00'
  const shots90 = minutes > 0 ? ((shots / minutes) * 90).toFixed(2) : '0.00'
  const sotPct = shots > 0 ? Math.round((sot / shots) * 100) : 0

  // Last 5 form from match logs
  const last5 = matchLogs.slice(0, 5)
  const last5Goals = last5.reduce((a, m) => a + (m.goals ?? 0), 0)
  const last5Assists = last5.reduce((a, m) => a + (m.assists ?? 0), 0)
  const last5Wins = last5.filter(m => m.result?.endsWith('W')).length

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(4, 1fr)',
      gap: 12, marginBottom: 24
    }}>
      <Metric
        label="Season Goals (PL)"
        value={goals}
        sub={`in ${apps} apps · ${goals90}/90`}
        color="var(--green)"
      />
      <Metric
        label="Shots / 90"
        value={shots90}
        sub={`${shots} total · ${sotPct}% on target`}
        color="var(--blue)"
      />
      <Metric
        label="xG (Season)"
        value={xg.toFixed(2)}
        sub={`npxG: ${(s.npxG ?? 0).toFixed(2)} · delta: ${(goals - xg).toFixed(1)}`}
        color={goals >= xg ? 'var(--green)' : 'var(--amber)'}
      />
      <Metric
        label="Last 5 Form"
        value={`${last5Goals}G ${last5Assists}A`}
        sub={`${last5Wins}W in last 5`}
        color="var(--amber)"
      />
    </div>
  )
}
