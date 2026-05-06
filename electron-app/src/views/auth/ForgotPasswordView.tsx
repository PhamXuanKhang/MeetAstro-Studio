import { useState, useCallback } from 'react'
import { useAuthStore } from '../../store/authStore'
import { isSupabaseConfigured } from '../../lib/supabase'

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '10px 12px',
  border: '1px solid #cbd5e1',
  borderRadius: 8,
  fontSize: 13,
  outline: 'none',
  background: '#f8fafc',
  boxSizing: 'border-box',
}

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
        <h2 style={{ fontSize: 18, fontWeight: 800, color: '#0f172a', marginBottom: 16 }}>
          Email đã gửi
        </h2>
        <div
          style={{
            padding: '14px 16px',
            background: '#dcfce7',
            borderRadius: 8,
            fontSize: 13,
            color: '#166534',
            marginBottom: 20,
          }}
        >
          Link đặt lại mật khẩu đã được gửi đến <strong>{email}</strong>. Vui lòng kiểm tra hộp thư.
        </div>
        <button
          onClick={onGoLogin}
          style={{ background: 'none', border: 'none', color: '#0ea5e9', cursor: 'pointer', fontSize: 13, padding: 0 }}
        >
          ← Quay lại đăng nhập
        </button>
      </>
    )
  }

  return (
    <>
      <h2 style={{ fontSize: 18, fontWeight: 800, color: '#0f172a', marginBottom: 8 }}>
        Quên mật khẩu
      </h2>
      <p style={{ fontSize: 13, color: '#64748b', marginBottom: 24 }}>
        Nhập email tài khoản — chúng tôi sẽ gửi link đặt lại mật khẩu.
      </p>

      {error && (
        <div
          style={{
            marginBottom: 16,
            padding: '10px 14px',
            background: '#fee2e2',
            borderRadius: 8,
            fontSize: 13,
            color: '#991b1b',
          }}
        >
          {error}
        </div>
      )}

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

        <button
          type="submit"
          disabled={loading || !isSupabaseConfigured}
          style={{
            padding: '10px 0',
            background: '#0ea5e9',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            fontWeight: 700,
            fontSize: 14,
            cursor: loading || !isSupabaseConfigured ? 'not-allowed' : 'pointer',
            opacity: loading || !isSupabaseConfigured ? 0.7 : 1,
            marginTop: 4,
          }}
        >
          {loading ? 'Đang gửi...' : 'Gửi link đặt lại'}
        </button>
      </form>

      <div style={{ marginTop: 20, textAlign: 'center' }}>
        <button
          onClick={onGoLogin}
          style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 13, padding: 0 }}
        >
          ← Quay lại đăng nhập
        </button>
      </div>
    </>
  )
}
