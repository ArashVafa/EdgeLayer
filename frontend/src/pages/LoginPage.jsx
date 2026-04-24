import { useState } from 'react'
import { useAuth } from '../context/AuthContext'

const S = {
  wrap: {
    minHeight: '100vh', display: 'flex', alignItems: 'center',
    justifyContent: 'center', padding: 24,
  },
  card: {
    width: '100%', maxWidth: 400,
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: 16, padding: 40,
  },
  logo: {
    display: 'flex', alignItems: 'center', gap: 10, marginBottom: 32,
    justifyContent: 'center',
  },
  logoMark: {
    width: 36, height: 36, borderRadius: 8,
    background: 'linear-gradient(135deg, #06b6d4, #3b82f6)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    fontWeight: 800, fontSize: 14, color: '#fff',
  },
  logoText: { fontSize: 20, fontWeight: 700, letterSpacing: '-0.5px' },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 6, textAlign: 'center' },
  sub: { fontSize: 13, color: 'var(--text-dim)', textAlign: 'center', marginBottom: 28 },
  label: { fontSize: 12, fontWeight: 600, color: 'var(--text-dim)', marginBottom: 6, display: 'block' },
  input: {
    width: '100%', padding: '10px 14px', borderRadius: 8, fontSize: 14,
    background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text)',
    outline: 'none', boxSizing: 'border-box', marginBottom: 16,
  },
  btn: {
    width: '100%', padding: '11px 0', borderRadius: 8, fontSize: 14, fontWeight: 600,
    background: 'linear-gradient(135deg, #06b6d4, #3b82f6)',
    color: '#fff', border: 'none', cursor: 'pointer', marginTop: 4,
  },
  error: {
    fontSize: 13, color: 'var(--red)', background: 'rgba(239,68,68,0.08)',
    border: '1px solid rgba(239,68,68,0.2)', borderRadius: 8,
    padding: '10px 14px', marginBottom: 16,
  },
  link: { color: 'var(--cyan)', cursor: 'pointer', textDecoration: 'underline' },
  footer: { textAlign: 'center', fontSize: 13, color: 'var(--text-dim)', marginTop: 20 },
}

export default function LoginPage({ onNavigate }) {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={S.wrap}>
      <div style={S.card}>
        <div style={S.logo}>
          <div style={S.logoMark}>EL</div>
          <div style={S.logoText}>Edge<span style={{ color: 'var(--cyan)' }}>Layer</span></div>
        </div>
        <div style={S.title}>Welcome back</div>
        <div style={S.sub}>Sign in to your account</div>

        <form onSubmit={submit}>
          {error && <div style={S.error}>{error}</div>}
          <label style={S.label}>Email</label>
          <input
            style={S.input} type="email" value={email} required autoFocus
            onChange={e => setEmail(e.target.value)} placeholder="you@example.com"
          />
          <label style={S.label}>Password</label>
          <input
            style={S.input} type="password" value={password} required
            onChange={e => setPassword(e.target.value)} placeholder="••••••••"
          />
          <div style={{ textAlign: 'right', marginTop: -8, marginBottom: 16 }}>
            <span style={{ ...S.link, fontSize: 12 }} onClick={() => onNavigate('forgot')}>
              Forgot password?
            </span>
          </div>
          <button style={S.btn} type="submit" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <div style={S.footer}>
          Don't have an account?{' '}
          <span style={S.link} onClick={() => onNavigate('register')}>Sign up</span>
        </div>
      </div>
    </div>
  )
}
