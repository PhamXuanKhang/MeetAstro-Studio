import { useState, useCallback } from 'react'
import { useAuthStore } from '../../store/authStore'
import { isSupabaseConfigured } from '../../lib/supabase'
import { Button, Field, Icon, Input } from '../../components/ui'
import { alertError, alertWarning } from '../../styles/designTokens'

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
      <h2 style={{ fontSize: 20, fontWeight: 800, color: 'var(--color-text-main)', margin: '0 0 6px', letterSpacing: '-0.02em' }}>
        Đăng nhập
      </h2>
      <p style={{ fontSize: 14, color: 'var(--color-text-muted)', margin: '0 0 24px' }}>
        Tiếp tục vào workspace xử lý biên bản họp.
      </p>

      {!isSupabaseConfigured && (
        <div style={{ ...alertWarning, marginBottom: 16 }}>
          Supabase chưa được cấu hình. Vui lòng thêm{' '}
          <code>VITE_SUPABASE_URL</code> và <code>VITE_SUPABASE_ANON_KEY</code> vào{' '}
          <code>.env</code>.
        </div>
      )}

      {error && <div style={{ ...alertError, marginBottom: 16 }}>{error}</div>}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <Field label="Email" required>
          <Input
            type="email"
            placeholder="you@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
        </Field>
        <Field label="Mật khẩu" required>
          <Input
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </Field>

        <Button type="submit" variant="primary" disabled={loading || !isSupabaseConfigured} style={{ width: '100%', marginTop: 4 }}>
          {loading && <Icon name="progress_activity" size={18} style={{ animation: 'spin 1s linear infinite' }} />}
          {loading ? 'Đang đăng nhập...' : 'Đăng nhập'}
        </Button>
      </form>

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '18px 0', color: 'var(--color-text-subtle)', fontSize: 12 }}>
        <div style={{ flex: 1, height: 1, background: 'var(--color-border-subtle)' }} />
        hoặc
        <div style={{ flex: 1, height: 1, background: 'var(--color-border-subtle)' }} />
      </div>

      <Button type="button" variant="secondary" onClick={handleGoogle} disabled={loading || !isSupabaseConfigured} style={{ width: '100%' }}>
        <Icon name="open_in_new" size={18} />
        Tiếp tục với Google
      </Button>

      <div style={{ marginTop: 20, display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
        <button onClick={onGoRegister} style={{ background: 'none', border: 'none', color: 'var(--color-primary)', cursor: 'pointer', fontSize: 13, padding: 0, fontWeight: 700 }}>
          Tạo tài khoản
        </button>
        <button onClick={onGoForgot} style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer', fontSize: 13, padding: 0 }}>
          Quên mật khẩu?
        </button>
      </div>
    </>
  )
}
