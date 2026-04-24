// Circular SVG score ring — stroke-dashoffset animated based on score
export default function EdgeScore({ score = 0 }) {
  const r = 62
  const circumference = 2 * Math.PI * r
  const offset = circumference * (1 - score / 100)

  const color =
    score >= 75 ? '#22c55e' :
    score >= 55 ? '#f59e0b' :
    '#ef4444'

  return (
    <div style={{
      width: 140, height: 140, position: 'relative',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0,
    }}>
      <svg
        viewBox="0 0 140 140"
        style={{ position: 'absolute', inset: 0, transform: 'rotate(-90deg)' }}
      >
        <circle
          cx="70" cy="70" r={r}
          fill="none"
          stroke="rgba(255,255,255,0.04)"
          strokeWidth="8"
        />
        <circle
          cx="70" cy="70" r={r}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
      </svg>
      <div style={{ textAlign: 'center', zIndex: 1 }}>
        <div style={{
          fontFamily: 'var(--mono)', fontSize: 40, fontWeight: 700, color, lineHeight: 1
        }}>
          {score}
        </div>
        <div style={{
          fontSize: 11, color: 'var(--text-dim)',
          textTransform: 'uppercase', letterSpacing: 1, marginTop: 4
        }}>
          Edge Score
        </div>
      </div>
    </div>
  )
}
