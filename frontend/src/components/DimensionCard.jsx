function scoreBadgeClass(score) {
  if (score >= 75) return 'high'
  if (score >= 55) return 'mid'
  if (score >= 35) return 'low'
  return 'info'
}

export default function DimensionCard({ name, score, analysis, flags = [], weight }) {
  const badgeClass = scoreBadgeClass(score)

  return (
    <div style={{
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 12, padding: '18px 20px'
    }}>
      <div style={{
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', marginBottom: 12
      }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 600 }}>{name}</div>
          {weight != null && (
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
              Weight: {(weight * 100).toFixed(0)}%
            </div>
          )}
        </div>
        <span className={`score-badge ${badgeClass}`}>{score}/100</span>
      </div>
      <div style={{ fontSize: 13, color: 'var(--text-dim)', lineHeight: 1.6 }}>
        {analysis || 'No analysis available.'}
      </div>
      {flags.length > 0 && !flags.includes('stub') && (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 10 }}>
          {flags.map(f => (
            <span key={f} style={{
              fontSize: 10, padding: '2px 7px', borderRadius: 4,
              background: 'rgba(6,182,212,0.08)', color: 'var(--cyan)',
              border: '1px solid rgba(6,182,212,0.15)', fontFamily: 'var(--mono)',
              letterSpacing: 0.5
            }}>
              {f.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
