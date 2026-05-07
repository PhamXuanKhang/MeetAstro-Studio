import { useState, useCallback } from 'react'
import { useAuthStore } from '../../store/authStore'
import { isSupabaseConfigured } from '../../lib/supabase'
import { alertError, alertWarning, buttonPrimary, buttonSecondary, inputStyle } from '../../styles/designTokens'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

interface Props {
  onGoRegister: () => void
  onGoForgot: () => void
}

export default function LoginView({ onGoRegister, onGoForgot }: Props) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const { login, startGoogleOAuth, loading } = useAuthStore()

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      setError(null)
      if (!EMAIL_PATTERN.test(email.trim())) {
        setError('Email không hợp lệ.')
        return
      }
      if (password.length < 8) {
        setError('Mật khẩu phải có ít nhất 8 ký tự.')
        return
      }

      try {
        await login(email.trim(), password)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Email hoặc mật khẩu không đúng, hoặc tài khoản chưa xác thực.')
      }
    },
    [email, password, login]
  )

  const handleGoogle = useCallback(async () => {
    setError(null)
    try {
      await startGoogleOAuth()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không mở được Google OAuth.')
    }
  }, [startGoogleOAuth])

  return (
    <>
      <h2 style={{ fontSize: 18, fontWeight: 800, color: '#0f172a', marginBottom: 24 }}>
        Đăng nhập
      </h2>

      {!isSupabaseConfigured && (
        <div style={{ ...alertWarning, marginBottom: 16 }}>
          Supabase chưa được cấu hình. Vui lòng thêm{' '}
          <code>VITE_SUPABASE_URL</code> và <code>VITE_SUPABASE_ANON_KEY</code> vào{' '}
          <code>.env</code>.
        </div>
      )}

      {error && <div style={{ ...alertError, marginBottom: 16 }}>{error}</div>}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoComplete="email"
          style={inputStyle}
        />
        <input
          type="password"
          placeholder="Mật khẩu"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="current-password"
          style={inputStyle}
        />

        <button
          type="submit"
          disabled={loading || !isSupabaseConfigured}
          style={{ ...buttonPrimary, cursor: loading || !isSupabaseConfigured ? 'not-allowed' : 'pointer', opacity: loading || !isSupabaseConfigured ? 0.7 : 1, marginTop: 4 }}
        >
          {loading ? 'Đang đăng nhập...' : 'Đăng nhập'}
        </button>
      </form>

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '18px 0', color: '#94a3b8', fontSize: 12 }}>
        <div style={{ flex: 1, height: 1, background: '#e2e8f0' }} />
        hoặc
        <div style={{ flex: 1, height: 1, background: '#e2e8f0' }} />
      </div>

      <button
        type="button"
        onClick={handleGoogle}
        disabled={loading || !isSupabaseConfigured}
        style={{ ...buttonSecondary, width: '100%', opacity: loading || !isSupabaseConfigured ? 0.7 : 1, cursor: loading || !isSupabaseConfigured ? 'not-allowed' : 'pointer' }}
      >
        Tiếp tục với Google
      </button>

      <div style={{ marginTop: 20, display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
        <button
          onClick={onGoRegister}
          style={{ background: 'none', border: 'none', color: '#0ea5e9', cursor: 'pointer', fontSize: 13, padding: 0 }}
        >
          Tạo tài khoản
        </button>
        <button
          onClick={onGoForgot}
          style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 13, padding: 0 }}
        >
          Quên mật khẩu?
        </button>
      </div>
    </>
  )
}
