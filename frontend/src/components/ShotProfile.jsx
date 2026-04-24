function Bar({ label, value, maxValue = 100, color = 'var(--cyan)', unit = '%' }) {
  const pct = Math.min(100, (value / Math.max(maxValue, 1)) * 100)
  const colorGradients = {
    'var(--cyan)': 'linear-gradient(90deg, rgba(6,182,212,0.3), #06b6d4)',
    'var(--green)': 'linear-gradient(90deg, rgba(34,197,94,0.3), #22c55e)',
    'var(--amber)': 'linear-gradient(90deg, rgba(245,158,11,0.3), #f59e0b)',
    'var(--blue)': 'linear-gradient(90deg, rgba(59,130,246,0.3), #3b82f6)',
  }
  const gradient = colorGradients[color] || colorGradients['var(--cyan)']

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
      <div style={{ fontSize: 12, color: 'var(--text-dim)', width: 130, textAlign: 'right', flexShrink: 0 }}>
        {label}
      </div>
      <div style={{
        flex: 1, height: 22, background: 'var(--surface-3)',
        borderRadius: 4, overflow: 'hidden'
      }}>
        <div className="bar-fill" style={{ width: `${pct}%`, background: gradient }}>
          {unit === '%' ? `${Math.round(value)}%` : value}
        </div>
      </div>
    </div>
  )
}

export default function ShotProfile({ shotProfile, stats }) {
  if (!shotProfile && !stats) return null

  const sp = shotProfile || {}
  const s = Array.isArray(stats) ? stats[0] : (stats || {})

  const total = sp.total_shots ?? s.shots ?? 0
  const sot = sp.shots_on_target ?? s.shots_on_target ?? 0
  const sotPct = total > 0 ? (sot / total * 100) : 0
  const leftPct = sp.left_foot_pct ?? 50
  const rightPct = sp.right_foot_pct ?? 35
  const headerPct = sp.header_pct ?? 15
  const inBoxPct = sp.in_box_pct ?? 75
  const goals = sp.goals ?? s.goals ?? 0

  return (
    <div style={{ maxWidth: 600 }}>
      <Bar label="Left Foot" value={leftPct} color="var(--cyan)" />
      <Bar label="Right Foot" value={rightPct} color="var(--blue)" />
      <Bar label="Headers" value={headerPct} color="var(--amber)" />
      <Bar label="In-Box %" value={inBoxPct} color="var(--green)" />
      <Bar label="Shot on Target %" value={sotPct} color="var(--cyan)" />
      <Bar
        label="Total Shots"
        value={total}
        maxValue={Math.max(total, 50)}
        unit="count"
        color="var(--green)"
      />
    </div>
  )
}
