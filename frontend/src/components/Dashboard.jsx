import { useEffect, useState } from 'react'
import { getReport, refreshReport } from '../api.js'
import EdgeScore from './EdgeScore.jsx'
import MatchStrip from './MatchStrip.jsx'
import MetricsGrid from './MetricsGrid.jsx'
import MatchLog from './MatchLog.jsx'
import ShotProfile from './ShotProfile.jsx'
import DimensionCard from './DimensionCard.jsx'
import RiskIndicators from './RiskIndicators.jsx'
import NarrativePanel from './NarrativePanel.jsx'

const SECTION = ({ title, children }) => (
  <div style={{ marginBottom: 24 }}>
    <div className="section-title">{title}</div>
    {children}
  </div>
)

export default function Dashboard({ playerId, player, onBack }) {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getReport(playerId)
      .then(setReport)
      .catch(e => setError(e.response?.data?.detail || e.message))
      .finally(() => setLoading(false))
  }, [playerId])

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      const data = await getReport(playerId, true)
      setReport(data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message)
    } finally {
      setRefreshing(false)
    }
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '50vh', gap: 16 }}>
        <div className="spinner" />
        <div style={{ color: 'var(--text-dim)', fontSize: 14 }}>Generating report…</div>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{
        background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)',
        borderRadius: 12, padding: 24, marginBottom: 24
      }}>
        <div style={{ color: 'var(--red)', fontWeight: 600, marginBottom: 8 }}>Report Error</div>
        <div style={{ color: 'var(--text-dim)', fontSize: 13 }}>{error}</div>
        <div style={{ marginTop: 8, fontSize: 12, color: 'var(--text-muted)' }}>
          Make sure you've run the Understat scrape first: POST /api/admin/scrape/understat
        </div>
        <button onClick={onBack} style={{
          marginTop: 16, padding: '8px 16px', borderRadius: 8, fontSize: 13,
          background: 'var(--surface)', border: '1px solid var(--border)',
          color: 'var(--text)', cursor: 'pointer', fontFamily: 'var(--sans)'
        }}>
          ← Back to search
        </button>
      </div>
    )
  }

  if (!report) return null

  const p = report.player || player
  const stats = Array.isArray(report.stats) ? report.stats[0] : report.stats
  const dims = report.dimensions || {}
  const dimList = Object.entries(dims)

  return (
    <div>
      {/* Back + refresh bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <button onClick={onBack} style={{
          display: 'flex', alignItems: 'center', gap: 6,
          background: 'none', border: '1px solid var(--border)',
          borderRadius: 8, padding: '6px 12px', color: 'var(--text-dim)',
          cursor: 'pointer', fontSize: 13, fontFamily: 'var(--sans)'
        }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="m15 18-6-6 6-6" />
          </svg>
          Back
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {report.from_cache && (
            <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>
              CACHED · {report.cached_at?.slice(0, 16) || ''}
            </div>
          )}
          <button onClick={handleRefresh} disabled={refreshing} style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 8, padding: '6px 12px', color: refreshing ? 'var(--text-muted)' : 'var(--cyan)',
            cursor: refreshing ? 'not-allowed' : 'pointer', fontSize: 13,
            fontFamily: 'var(--sans)', transition: 'all 0.15s'
          }}>
            {refreshing ? (
              <><div className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> Refreshing…</>
            ) : (
              <>↻ Refresh Report</>
            )}
          </button>
        </div>
      </div>

      {/* Player Banner */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr auto', gap: 32,
        alignItems: 'center',
        background: 'var(--surface)', border: '1px solid var(--border)',
        borderRadius: 16, padding: '28px 32px', marginBottom: 24,
        position: 'relative', overflow: 'hidden'
      }}>
        {/* Background glow */}
        <div style={{
          position: 'absolute', top: -60, right: -60, width: 200, height: 200,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(6,182,212,0.08), transparent)',
          pointerEvents: 'none'
        }} />

        <div>
          <h1 style={{ fontSize: 32, fontWeight: 800, letterSpacing: -1, marginBottom: 4 }}>
            {p?.name}
          </h1>
          <div style={{ fontSize: 14, color: 'var(--text-dim)', display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 8 }}>
            <span>{p?.team}</span>
            <Dot />
            <span>{p?.position || 'Unknown'}</span>
            {report.opponent && (<><Dot /><span>Next: {report.opponent}</span></>)}
            {report.from_cache && <span style={{ color: 'var(--amber)' }}>· Cached</span>}
          </div>
        </div>

        <EdgeScore score={report.edge_score} />
      </div>

      {/* Match Strip */}
      <MatchStrip fixture={report.fixture} playerTeam={p?.team} />

      {/* Key Metrics */}
      <MetricsGrid stats={report.stats} matchLogs={report.match_logs || []} />

      {/* Recent Match Log */}
      <SECTION title="Recent Match Log">
        <MatchLog logs={report.match_logs || []} />
      </SECTION>

      {/* Shot Profile */}
      <SECTION title="Shot Profile">
        <ShotProfile shotProfile={report.shot_profile} stats={report.stats} />
      </SECTION>

      {/* Dimension Cards */}
      <SECTION title="13-Dimension Analysis">
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12
        }}>
          {dimList.map(([key, dim]) => (
            <DimensionCard
              key={key}
              name={dim.name}
              score={dim.score}
              analysis={dim.analysis}
              flags={dim.flags || []}
              weight={dim.weight}
            />
          ))}
        </div>
      </SECTION>

      {/* Risk Indicators */}
      <SECTION title="Risk Summary">
        <RiskIndicators
          riskSummary={report.risk_summary}
          confidence={report.confidence}
          riskLevel={report.risk_level}
          marketData={report.market_data}
        />
      </SECTION>

      {/* Narrative Panel */}
      <SECTION title="Narrative Analysis">
        <NarrativePanel narratives={report.narratives || {}} />
      </SECTION>

      {/* Output Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 24 }}>
        <OutputMetric label="Edge Score" value={report.edge_score} color="var(--green)" sub="out of 100" />
        <OutputMetric label="Confidence" value={report.confidence} color={report.confidence === 'HIGH' ? 'var(--green)' : report.confidence === 'MEDIUM' ? 'var(--amber)' : 'var(--red)'} sub="threshold" />
        <OutputMetric label="Risk Level" value={report.risk_level} color={report.risk_level === 'LOW' ? 'var(--green)' : report.risk_level === 'MEDIUM' ? 'var(--amber)' : 'var(--red)'} sub="risk flags" />
        <OutputMetric label="Opponent" value={report.opponent || 'TBD'} color="var(--blue)" sub="next fixture" />
      </div>
    </div>
  )
}

function Dot() {
  return <span style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--text-muted)', display: 'inline-block', marginTop: 7, flexShrink: 0 }} />
}

function OutputMetric({ label, value, color, sub }) {
  return (
    <div style={{
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 12, padding: '16px 18px'
    }}>
      <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.8px', color: 'var(--text-dim)', marginBottom: 8, fontWeight: 500 }}>
        {label}
      </div>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 22, fontWeight: 700, color }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4 }}>{sub}</div>}
    </div>
  )
}
