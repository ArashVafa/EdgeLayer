function RiskItem({ label, value, level }) {
  const colorMap = { LOW: 'var(--green)', MEDIUM: 'var(--amber)', HIGH: 'var(--red)', NONE: 'var(--green)' }
  const color = colorMap[level?.toUpperCase()] || 'var(--text-dim)'
  return (
    <div style={{
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 10, padding: '14px 16px', textAlign: 'center'
    }}>
      <div style={{ fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.6px', color: 'var(--text-dim)', marginBottom: 6 }}>
        {label}
      </div>
      <div style={{ fontFamily: 'var(--mono)', fontSize: 18, fontWeight: 700, color }}>
        {value}
      </div>
    </div>
  )
}

export default function RiskIndicators({ riskSummary, confidence, riskLevel, marketData }) {
  if (!riskSummary) return null

  const rotationRisk = riskSummary.rotation_risk || 'LOW'
  const injuryFlag = riskSummary.injury_flag ? 'YES' : 'NONE'
  const earlySubPct = riskSummary.early_sub_pct != null ? `${riskSummary.early_sub_pct}%` : '<10%'
  const lineupCertainty = riskSummary.lineup_certainty != null ? `${riskSummary.lineup_certainty}%` : '85%'
  const edgePct = marketData?.edge_pct != null ? `${marketData.edge_pct > 0 ? '+' : ''}${marketData.edge_pct}%` : 'N/A'

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(3, 1fr)',
      gap: 10
    }}>
      <RiskItem label="Rotation Risk" value={rotationRisk} level={rotationRisk} />
      <RiskItem label="Injury Risk" value={injuryFlag} level={injuryFlag === 'NONE' ? 'NONE' : 'HIGH'} />
      <RiskItem label="Early Sub Prob" value={earlySubPct} level={riskSummary.early_sub_pct > 30 ? 'HIGH' : riskSummary.early_sub_pct > 15 ? 'MEDIUM' : 'LOW'} />
      <RiskItem label="Lineup Certainty" value={lineupCertainty} level={riskSummary.lineup_certainty > 80 ? 'LOW' : riskSummary.lineup_certainty > 60 ? 'MEDIUM' : 'HIGH'} />
      <RiskItem label="Market Edge" value={edgePct} level={marketData?.edge_pct > 5 ? 'LOW' : marketData?.edge_pct > 0 ? 'MEDIUM' : 'HIGH'} />
      <RiskItem label="Overall Risk" value={riskLevel || 'MEDIUM'} level={riskLevel || 'MEDIUM'} />
    </div>
  )
}
