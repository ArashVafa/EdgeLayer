import { useState } from 'react'
import PlayerSearch from './components/PlayerSearch.jsx'
import Dashboard from './components/Dashboard.jsx'

export default function App() {
  const [selectedPlayer, setSelectedPlayer] = useState(null)

  return (
    <>
      <div className="noise-overlay" />
      <div style={{ maxWidth: 1280, margin: '0 auto', padding: '24px', position: 'relative', zIndex: 1 }}>
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          marginBottom: 32, paddingBottom: 20,
          borderBottom: '1px solid var(--border)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 36, height: 36, borderRadius: 8,
              background: 'linear-gradient(135deg, #06b6d4, #3b82f6)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontWeight: 800, fontSize: 14, color: '#fff', cursor: 'pointer',
            }} onClick={() => setSelectedPlayer(null)}>
              EL
            </div>
            <div style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.5px', cursor: 'pointer' }}
              onClick={() => setSelectedPlayer(null)}>
              Edge<span style={{ color: 'var(--cyan)' }}>Layer</span>
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontFamily: 'var(--mono)', fontSize: 12, color: 'var(--text-dim)' }}>
              {new Date().toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }).toUpperCase()} — PRE-MATCH INTEL
            </div>
            <div style={{
              display: 'inline-block', padding: '4px 10px', borderRadius: 6,
              fontSize: 11, fontWeight: 600,
              background: 'rgba(34,197,94,0.08)', color: 'var(--green)',
              border: '1px solid rgba(34,197,94,0.2)', marginTop: 4
            }}>
              LIVE DATA
            </div>
          </div>
        </div>

        {/* Main content */}
        {!selectedPlayer ? (
          <LandingPage onSelect={setSelectedPlayer} />
        ) : (
          <Dashboard playerId={selectedPlayer.id} player={selectedPlayer} onBack={() => setSelectedPlayer(null)} />
        )}

        {/* Footer */}
        <div style={{
          textAlign: 'center', padding: '32px 0 16px',
          fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.8
        }}>
          EdgeLayer is an analytical tool for informational purposes only.<br />
          Gambling involves risk. Please bet responsibly and within your means.<br />
          Data sourced from Understat, football-data.org, and The Odds API.<br />
          © 2026 EdgeLayer
        </div>
      </div>
    </>
  )
}

function LandingPage({ onSelect }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', minHeight: '60vh', gap: 32
    }}>
      {/* Hero */}
      <div style={{ textAlign: 'center' }}>
        <div style={{
          fontFamily: 'var(--mono)', fontSize: 11, letterSpacing: 4,
          color: 'var(--cyan)', marginBottom: 16, textTransform: 'uppercase'
        }}>
          Premier League Intelligence
        </div>
        <h1 style={{
          fontSize: 48, fontWeight: 800, letterSpacing: -2,
          lineHeight: 1.1, marginBottom: 16
        }}>
          Pre-Bet <span style={{ color: 'var(--cyan)' }}>Intelligence</span><br />
          for Every Player
        </h1>
        <p style={{ fontSize: 16, color: 'var(--text-dim)', maxWidth: 480, lineHeight: 1.6 }}>
          Search any Premier League player to get a data-driven Edge Score,
          13-dimension analysis, and AI-generated betting narratives.
        </p>
      </div>

      {/* Search */}
      <div style={{ width: '100%', maxWidth: 560 }}>
        <PlayerSearch onSelect={onSelect} />
      </div>

      {/* Feature pills */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', justifyContent: 'center' }}>
        {[
          '13 Data Dimensions',
          'xG & Shot Analysis',
          'Market Intelligence',
          'Injury Signals',
          'AI Narratives',
          'Risk Assessment',
        ].map(f => (
          <div key={f} style={{
            padding: '6px 14px', borderRadius: 20, fontSize: 12, fontWeight: 500,
            background: 'var(--surface)', border: '1px solid var(--border)',
            color: 'var(--text-dim)'
          }}>
            {f}
          </div>
        ))}
      </div>
    </div>
  )
}
