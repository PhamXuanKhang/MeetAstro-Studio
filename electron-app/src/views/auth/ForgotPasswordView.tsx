import { useState, useCallback } from 'react'
import { useAuthStore } from '../../store/authStore'
import { isSupabaseConfigured } from '../../lib/supabase'
import { Button, Field, Icon, Input } from '../../components/ui'
import { alertError, alertSuccess, alertWarning } from '../../styles/designTokens'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

interface Props {
  onGoLogin: () => void
}

export default function ForgotPasswordView({ onGoLogin }: Props) {
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [sent, setSent] = useState(false)
  const { forgotPassword, loading } = useAuthStore()

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      setError(null)
      if (!EMAIL_PATTERN.test(email.trim())) {
        setError('Email không hợp lệ.')
        return
      }
      try {
        await forgotPassword(email.trim())
        setSent(true)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Không gửi được email.')
      }
    },
    [email, forgotPassword]
  )

  if (sent) {
    return (
      <>
        <h2 style={{ fontSize: 20, fontWeight: 800, color: 'var(--color-text-main)', margin: '0 0 16px' }}>
          Email đã gửi
        </h2>
        <div style={{ ...alertSuccess, marginBottom: 20 }}>
          Link đặt lại mật khẩu đã được gửi đến <strong>{email}</strong>. Vui lòng kiểm tra hộp thư.
        </div>
        <button onClick={onGoLogin} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'none', border: 'none', color: 'var(--color-primary)', cursor: 'pointer', fontSize: 13, padding: 0, fontWeight: 700 }}>
          <Icon name="arrow_back" size={14} /> Quay lại đăng nhập
        </button>
      </>
    )
  }

  return (
    <>
      <h2 style={{ fontSize: 20, fontWeight: 800, color: 'var(--color-text-main)', margin: '0 0 8px' }}>
        Quên mật khẩu
      </h2>
      <p style={{ fontSize: 14, color: 'var(--color-text-muted)', margin: '0 0 24px', lineHeight: 1.6 }}>
        Nhập email tài khoản — chúng tôi sẽ gửi link đặt lại mật khẩu.
      </p>

      {!isSupabaseConfigured && (
        <div style={{ ...alertWarning, marginBottom: 16 }}>
          Supabase chưa được cấu hình. Vui lòng thêm <code>VITE_SUPABASE_URL</code> và{' '}
          <code>VITE_SUPABASE_ANON_KEY</code> vào <code>.env</code>.
        </div>
      )}

      {error && <div style={{ ...alertError, marginBottom: 16 }}>{error}</div>}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <Field label="Email" required>
          <Input type="email" placeholder="you@company.com" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
        </Field>

        <Button type="submit" variant="primary" disabled={loading || !isSupabaseConfigured} style={{ width: '100%', marginTop: 4 }}>
          {loading && <Icon name="progress_activity" size={18} style={{ animation: 'spin 1s linear infinite' }} />}
          {loading ? 'Đang gửi...' : 'Gửi link đặt lại'}
        </Button>
      </form>

      <div style={{ marginTop: 20, textAlign: 'center' }}>
        <button onClick={onGoLogin} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'none', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer', fontSize: 13, padding: 0 }}>
          <Icon name="arrow_back" size={14} /> Quay lại đăng nhập
        </button>
      </div>
    </>
  )
}


