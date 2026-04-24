import { useState } from 'react'
import { authApi } from '../api'

const S = {
  wrap: {
    minHeight: '100vh', display: 'flex', alignItems: 'center',
    justifyContent: 'center', padding: 24,
  },
  card: {
    width: '100%', maxWidth: 400,
    background: 'var(--surface)', border: '1px solid var(--border)',
    borderRadius: 16, padding: 40,
  },
  back: {
    fontSize: 13, color: 'var(--text-dim)', cursor: 'pointer',
    marginBottom: 28, display: 'inline-flex', alignItems: 'center', gap: 6,
  },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 6 },
  sub: { fontSize: 13, color: 'var(--text-dim)', marginBottom: 28, lineHeight: 1.6 },
  label: { fontSize: 12, fontWeight: 600, color: 'var(--text-dim)', marginBottom: 6, display: 'block' },
  input: {
    width: '100%', padding: '10px 14px', borderRadius: 8, fontSize: 14,
    background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text)',
    outline: 'none', boxSizing: 'border-box', marginBottom: 16,
  },
  btn: {
    width: '100%', padding: '11px 0', borderRadius: 8, fontSize: 14, fontWeight: 600,
    background: 'linear-gradient(135deg, #06b6d4, #3b82f6)',
    color: '#fff', border: 'none', cursor: 'pointer',
  },
  error: {
    fontSize: 13, color: 'var(--red)', background: 'rgba(239,68,68,0.08)',
    border: '1px solid rgba(239,68,68,0.2)', borderRadius: 8,
    padding: '10px 14px', marginBottom: 16,
  },
  success: {
    fontSize: 13, color: 'var(--green)', background: 'rgba(34,197,94,0.08)',
    border: '1px solid rgba(34,197,94,0.2)', borderRadius: 8,
    padding: '10px 14px', marginBottom: 16,
  },
}

export default function ForgotPasswordPage({ onNavigate }) {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await authApi.forgotPassword(email)
      setSent(true)
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={S.wrap}>
      <div style={S.card}>
        <span style={S.back} onClick={() => onNavigate('login')}>← Back to sign in</span>
        <div style={S.title}>Reset password</div>
        <div style={S.sub}>
          Enter your email and we'll send you a link to reset your password.
        </div>

        {sent ? (
          <div style={S.success}>
            Check your inbox — a reset link has been sent if that email exists.
          </div>
        ) : (
          <form onSubmit={submit}>
            {error && <div style={S.error}>{error}</div>}
            <label style={S.label}>Email</label>
            <input
              style={S.input} type="email" value={email} required autoFocus
              onChange={e => setEmail(e.target.value)} placeholder="you@example.com"
            />
            <button style={S.btn} type="submit" disabled={loading}>
              {loading ? 'Sending…' : 'Send reset link'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
