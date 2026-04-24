import { useState, useRef, useEffect } from 'react'
import api from '../api.js'

const STARTERS = [
  'What are his chances of scoring next game?',
  'Is he worth backing for anytime scorer?',
  'What are the main risks with this pick?',
  'How has he performed away from home this season?',
]

export default function ChatPanel({ playerId, playerName }) {
  const [history, setHistory] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history, loading])

  const send = async (text) => {
    const msg = text || input.trim()
    if (!msg || loading) return
    setInput('')

    const userMsg = { role: 'user', content: msg }
    setHistory(h => [...h, userMsg])
    setLoading(true)

    try {
      const { reply } = await api
        .post(`/api/chat/${playerId}`, { message: msg, history })
        .then(r => r.data)
      setHistory(h => [...h, { role: 'assistant', content: reply }])
    } catch (err) {
      setHistory(h => [...h, {
        role: 'assistant',
        content: 'Sorry, something went wrong. Please try again.',
      }])
    } finally {
      setLoading(false)
    }
  }

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  return (
    <div style={{
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 16, overflow: 'hidden', display: 'flex', flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <div style={{
          width: 28, height: 28, borderRadius: 8,
          background: 'linear-gradient(135deg, #8b5cf6, #06b6d4)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 13,
        }}>✦</div>
        <div>
          <div style={{ fontWeight: 600, fontSize: 14 }}>Ask about {playerName}</div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>
            Powered by Claude · Add your own context to any question
          </div>
        </div>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1, minHeight: 280, maxHeight: 480,
        overflowY: 'auto', padding: '16px 20px',
        display: 'flex', flexDirection: 'column', gap: 12,
      }}>
        {history.length === 0 && (
          <div>
            <div style={{ fontSize: 13, color: 'var(--text-dim)', marginBottom: 12 }}>
              Ask anything about this player — or add context like transfer news, injuries, or team form.
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {STARTERS.map(q => (
                <button key={q} onClick={() => send(q)} style={{
                  textAlign: 'left', padding: '9px 14px', borderRadius: 8,
                  fontSize: 13, color: 'var(--text-dim)',
                  background: 'var(--bg)', border: '1px solid var(--border)',
                  cursor: 'pointer', fontFamily: 'var(--sans)',
                  transition: 'border-color 0.15s',
                }}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {history.map((msg, i) => (
          <div key={i} style={{
            display: 'flex',
            justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
          }}>
            <div style={{
              maxWidth: '82%',
              padding: '10px 14px', borderRadius: 12,
              fontSize: 13, lineHeight: 1.6,
              background: msg.role === 'user'
                ? 'linear-gradient(135deg, rgba(6,182,212,0.15), rgba(59,130,246,0.15))'
                : 'var(--bg)',
              border: '1px solid var(--border)',
              color: 'var(--text)',
              whiteSpace: 'pre-wrap',
            }}>
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{
              padding: '10px 14px', borderRadius: 12, fontSize: 13,
              background: 'var(--bg)', border: '1px solid var(--border)',
              color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: 8,
            }}>
              <div className="spinner" style={{ width: 12, height: 12, borderWidth: 2 }} />
              Thinking…
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: '12px 16px', borderTop: '1px solid var(--border)',
        display: 'flex', gap: 8, alignItems: 'flex-end',
      }}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKey}
          placeholder={`Ask about ${playerName}… (e.g. "he's injured but playing through it, is he worth backing?")`}
          rows={1}
          style={{
            flex: 1, padding: '9px 12px', borderRadius: 8, fontSize: 13,
            background: 'var(--bg)', border: '1px solid var(--border)',
            color: 'var(--text)', outline: 'none', resize: 'none',
            fontFamily: 'var(--sans)', lineHeight: 1.5,
            maxHeight: 120, overflowY: 'auto',
          }}
        />
        <button
          onClick={() => send()}
          disabled={!input.trim() || loading}
          style={{
            padding: '9px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600,
            background: input.trim() && !loading
              ? 'linear-gradient(135deg, #06b6d4, #3b82f6)'
              : 'var(--border)',
            color: input.trim() && !loading ? '#fff' : 'var(--text-muted)',
            border: 'none', cursor: input.trim() && !loading ? 'pointer' : 'not-allowed',
            transition: 'all 0.15s', whiteSpace: 'nowrap',
          }}
        >
          Send
        </button>
      </div>
    </div>
  )
}
