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
  title: { fontSize: 22, fontWeight: 700, marginBottom: 6 },
  sub: { fontSize: 13, color: 'var(--text-dim)', marginBottom: 28 },
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
  link: { color: 'var(--cyan)', cursor: 'pointer', textDecoration: 'underline' },
}

export default function ResetPasswordPage({ token, onNavigate }) {
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    if (password !== confirm) { setError('Passwords do not match'); return }
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }
    setLoading(true)
    try {
      await authApi.resetPassword(token, password)
      setDone(true)
    } catch (err) {
      setError(err.response?.data?.detail || 'Reset failed. The link may have expired.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={S.wrap}>
      <div style={S.card}>
        <div style={S.title}>Set new password</div>
        <div style={S.sub}>Choose a strong password for your account.</div>

        {done ? (
          <>
            <div style={S.success}>Password updated successfully!</div>
            <span style={S.link} onClick={() => onNavigate('login')}>Sign in with new password →</span>
          </>
        ) : (
          <form onSubmit={submit}>
            {error && <div style={S.error}>{error}</div>}
            <label style={S.label}>New password</label>
            <input
              style={S.input} type="password" value={password} required autoFocus
              onChange={e => setPassword(e.target.value)} placeholder="Min. 8 characters"
            />
            <label style={S.label}>Confirm new password</label>
            <input
              style={S.input} type="password" value={confirm} required
              onChange={e => setConfirm(e.target.value)} placeholder="••••••••"
            />
            <button style={S.btn} type="submit" disabled={loading}>
              {loading ? 'Updating…' : 'Update password'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
