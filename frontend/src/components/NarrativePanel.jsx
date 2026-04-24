import { useState } from 'react'

const TABS = [
  { key: 'average', label: 'Average' },
  { key: 'aggressive', label: 'Aggressive' },
  { key: 'conservative', label: 'Conservative' },
]

export default function NarrativePanel({ narratives = {} }) {
  const [active, setActive] = useState('average')

  const text = narratives[active] || 'No narrative available.'

  // Split on double newlines or sentence-like breaks for paragraphs
  const paragraphs = text.split(/\n\n+/).filter(Boolean)

  return (
    <div>
      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActive(tab.key)}
            style={{
              padding: '8px 16px', borderRadius: 8, fontSize: 13, fontWeight: 500,
              background: active === tab.key ? 'var(--cyan)' : 'var(--surface)',
              border: `1px solid ${active === tab.key ? 'var(--cyan)' : 'var(--border)'}`,
              color: active === tab.key ? '#0b0e11' : 'var(--text-dim)',
              cursor: 'pointer', fontFamily: 'var(--sans)',
              transition: 'all 0.15s',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 14, padding: '24px 28px'
      }}>
        {paragraphs.length > 0 ? paragraphs.map((p, i) => (
          <p key={i} style={{
            fontSize: 14, color: 'var(--text-dim)', lineHeight: 1.75,
            marginBottom: i < paragraphs.length - 1 ? 12 : 0
          }}>
            {p}
          </p>
        )) : (
          <p style={{ fontSize: 14, color: 'var(--text-dim)', lineHeight: 1.75 }}>
            {text}
          </p>
        )}
      </div>
    </div>
  )
}
