export default function MatchStrip({ fixture, playerTeam }) {
  if (!fixture) {
    return (
      <div style={{
        background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12,
        padding: '20px 24px', marginBottom: 24, textAlign: 'center',
        color: 'var(--text-muted)', fontSize: 14
      }}>
        No upcoming fixture found. Run fixture scrape to populate schedule.
      </div>
    )
  }

  const { home_team, away_team, date, score } = fixture

  // Format date
  let dateStr = date || ''
  let timeStr = ''
  try {
    const d = new Date(date)
    dateStr = d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
    timeStr = d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) + ' BST'
  } catch {}

  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '1fr auto 1fr',
      gap: 16, alignItems: 'center',
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 12, padding: '20px 24px', marginBottom: 24,
      textAlign: 'center'
    }}>
      <div style={{ fontSize: 18, fontWeight: 700, textAlign: 'right' }}>
        {home_team}
      </div>
      <div style={{
        fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--text-muted)',
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4
      }}>
        {score ? (
          <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--text)', fontFamily: 'var(--mono)' }}>
            {score}
          </div>
        ) : (
          <div style={{ fontSize: 14, color: 'var(--amber)', fontWeight: 600 }}>{timeStr}</div>
        )}
        <div>{dateStr}</div>
        <div style={{ color: 'var(--cyan)', fontSize: 11 }}>Premier League</div>
      </div>
      <div style={{ fontSize: 18, fontWeight: 700, textAlign: 'left' }}>
        {away_team}
      </div>
    </div>
  )
}
