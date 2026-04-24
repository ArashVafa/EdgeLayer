import { useState, useEffect, useRef } from 'react'
import { searchPlayers } from '../api.js'

export default function PlayerSearch({ onSelect }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const debounceRef = useRef(null)
  const wrapperRef = useRef(null)

  useEffect(() => {
    const handler = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (query.trim().length < 2) {
      setResults([])
      setOpen(false)
      return
    }
    debounceRef.current = setTimeout(async () => {
      setLoading(true)
      try {
        const data = await searchPlayers(query.trim())
        setResults(data.players || [])
        setOpen(true)
      } catch {
        setResults([])
      } finally {
        setLoading(false)
      }
    }, 300)
  }, [query])

  const handleSelect = (player) => {
    setQuery(player.name)
    setOpen(false)
    onSelect(player)
  }

  return (
    <div ref={wrapperRef} style={{ position: 'relative', width: '100%' }}>
      <div style={{
        position: 'relative',
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: open && results.length > 0 ? '12px 12px 0 0' : 12,
        overflow: 'visible',
      }}>
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onFocus={() => results.length > 0 && setOpen(true)}
          placeholder="Search player name… (e.g. Haaland, Salah, Saka)"
          style={{
            width: '100%',
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: 'var(--text)',
            fontSize: 16,
            padding: '16px 48px 16px 20px',
            fontFamily: 'var(--sans)',
          }}
        />
        <div style={{
          position: 'absolute', right: 16, top: '50%', transform: 'translateY(-50%)',
        }}>
          {loading ? (
            <div className="spinner" style={{ width: 18, height: 18, borderWidth: 2 }} />
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2">
              <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
            </svg>
          )}
        </div>
      </div>

      {open && results.length > 0 && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100,
          background: 'var(--surface)',
          border: '1px solid var(--border)', borderTop: 'none',
          borderRadius: '0 0 12px 12px',
          maxHeight: 320, overflowY: 'auto',
        }}>
          {results.map((p, i) => (
            <div
              key={p.id}
              onClick={() => handleSelect(p)}
              style={{
                padding: '12px 20px',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                cursor: 'pointer',
                borderBottom: i < results.length - 1 ? '1px solid var(--border)' : 'none',
              }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--surface-2)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
            >
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{p.name}</div>
                <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 2 }}>
                  {p.team} · {p.position || 'Unknown position'}
                </div>
              </div>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2">
                <path d="m9 18 6-6-6-6" />
              </svg>
            </div>
          ))}
        </div>
      )}

      {open && results.length === 0 && query.length >= 2 && !loading && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 100,
          background: 'var(--surface)',
          border: '1px solid var(--border)', borderTop: 'none',
          borderRadius: '0 0 12px 12px',
          padding: '16px 20px',
          color: 'var(--text-dim)', fontSize: 13,
        }}>
          No players found for "{query}". Try scraping data first via the admin panel.
        </div>
      )}
    </div>
  )
}
