import { useState } from 'react'
import { login, sendOtp, verifyOtp } from '../api'

export function Auth({ onLogin }) {
  const [mode, setMode] = useState('login') // 'login' | 'signup' | 'otp'
  const [form, setForm] = useState({ email: '', password: '', username: '', otp: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))

  async function run(fn) {
    setError('')
    setLoading(true)
    try {
      await fn()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleLogin(e) {
    e.preventDefault()
    await run(async () => {
      const { token } = await login(form.email, form.password)
      onLogin(token)
    })
  }

  async function handleSendOtp(e) {
    e.preventDefault()
    await run(async () => {
      await sendOtp(form.email, form.password, form.username)
      setMode('otp')
    })
  }

  async function handleVerifyOtp(e) {
    e.preventDefault()
    await run(async () => {
      await verifyOtp(form.email, form.otp)
      const { token } = await login(form.email, form.password)
      onLogin(token)
    })
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="auth-header">
          <h1>Random Thoughts</h1>
          <p className="muted">Content Signal &amp; Recommendation</p>
        </div>

        {mode !== 'otp' && (
          <div className="tabs">
            <button
              className={mode === 'login' ? 'tab active' : 'tab'}
              onClick={() => { setMode('login'); setError('') }}
            >
              Login
            </button>
            <button
              className={mode === 'signup' ? 'tab active' : 'tab'}
              onClick={() => { setMode('signup'); setError('') }}
            >
              Sign up
            </button>
          </div>
        )}

        {mode === 'login' && (
          <form onSubmit={handleLogin} className="form-stack">
            <input
              type="email"
              placeholder="Email"
              value={form.email}
              onChange={set('email')}
              required
            />
            <input
              type="password"
              placeholder="Password"
              value={form.password}
              onChange={set('password')}
              required
            />
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Logging in…' : 'Login'}
            </button>
          </form>
        )}

        {mode === 'signup' && (
          <form onSubmit={handleSendOtp} className="form-stack">
            <input
              type="text"
              placeholder="Username"
              value={form.username}
              onChange={set('username')}
              required
            />
            <input
              type="email"
              placeholder="Email"
              value={form.email}
              onChange={set('email')}
              required
            />
            <input
              type="password"
              placeholder="Password"
              value={form.password}
              onChange={set('password')}
              required
            />
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Sending OTP…' : 'Send OTP'}
            </button>
          </form>
        )}

        {mode === 'otp' && (
          <form onSubmit={handleVerifyOtp} className="form-stack">
            <div className="info-box">
              OTP printed to the authentication service stdout — check your docker logs.
            </div>
            <input
              type="text"
              placeholder="6-digit OTP"
              value={form.otp}
              onChange={set('otp')}
              maxLength={6}
              pattern="\d{6}"
              required
            />
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Verifying…' : 'Verify & Sign up'}
            </button>
            <button
              type="button"
              className="btn-ghost"
              onClick={() => { setMode('signup'); setError('') }}
            >
              Back
            </button>
          </form>
        )}

        {error && <p className="error-msg">{error}</p>}
      </div>
    </div>
  )
}
