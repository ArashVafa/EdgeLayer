function ResultPill({ result }) {
  if (!result) return null
  const char = result.slice(-1)
  const colorMap = { W: { bg: 'rgba(34,197,94,0.08)', color: '#22c55e' }, D: { bg: 'rgba(245,158,11,0.08)', color: '#f59e0b' }, L: { bg: 'rgba(239,68,68,0.08)', color: '#ef4444' } }
  const style = colorMap[char] || { bg: 'var(--surface-3)', color: 'var(--text-dim)' }
  const score = result.slice(0, -2).trim()
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 4,
      fontSize: 11, fontWeight: 700,
      background: style.bg, color: style.color,
      fontFamily: 'var(--mono)'
    }}>
      {score} {char}
    </span>
  )
}

export default function MatchLog({ logs = [] }) {
  if (!logs.length) {
    return (
      <div style={{
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 12, padding: 24, textAlign: 'center',
        color: 'var(--text-dim)', fontSize: 13
      }}>
        No match log data available.
      </div>
    )
  }

  const th = { textAlign: 'left', padding: '8px 12px', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.8px', color: 'var(--text-muted)', borderBottom: '1px solid var(--border)', fontWeight: 500, fontFamily: 'var(--sans)' }
  const td = { padding: '10px 12px', borderBottom: '1px solid var(--border)', fontFamily: 'var(--mono)', color: 'var(--text-dim)', fontSize: 13 }

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr>
            <th style={th}>Date</th>
            <th style={th}>Opponent</th>
            <th style={th}>H/A</th>
            <th style={th}>Result</th>
            <th style={th}>Min</th>
            <th style={{ ...th, color: 'var(--green)' }}>G</th>
            <th style={{ ...th, color: 'var(--blue)' }}>A</th>
            <th style={th}>Shots</th>
            <th style={th}>xG</th>
            <th style={th}>Rating</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((m, i) => {
            const xgNum = parseFloat(m.xG) || 0
            return (
              <tr key={i} style={{ cursor: 'default' }}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.02)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <td style={td}>{m.date?.slice(0, 10) || '—'}</td>
                <td style={{ ...td, color: 'var(--text)', fontWeight: 500 }}>{m.opponent || '—'}</td>
                <td style={td}>{m.home_away || '—'}</td>
                <td style={td}><ResultPill result={m.result} /></td>
                <td style={td}>{m.minutes ?? '—'}</td>
                <td style={{ ...td, color: m.goals > 0 ? 'var(--green)' : 'inherit' }}>{m.goals ?? 0}</td>
                <td style={{ ...td, color: m.assists > 0 ? '#3b82f6' : 'inherit' }}>{m.assists ?? 0}</td>
                <td style={td}>{m.shots ?? 0}</td>
                <td style={{ ...td, color: xgNum >= 0.7 ? 'var(--green)' : xgNum >= 0.3 ? 'var(--amber)' : 'inherit' }}>
                  {xgNum.toFixed(2)}
                </td>
                <td style={{ ...td, color: m.rating >= 7.5 ? 'var(--green)' : m.rating < 6 ? 'var(--red)' : 'inherit' }}>
                  {m.rating != null ? m.rating.toFixed(1) : '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
