import { useState, useCallback } from 'react'
import { useAuthStore } from '../../store/authStore'
import { isSupabaseConfigured } from '../../lib/supabase'
import { alertError, alertSuccess, alertWarning, buttonPrimary, buttonSecondary, inputStyle } from '../../styles/designTokens'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

interface Props {
  onGoLogin: () => void
}

export default function RegisterView({ onGoLogin }: Props) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)
  const { register, startGoogleOAuth, loading } = useAuthStore()

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      setError(null)
      setSuccessMsg(null)

      if (!EMAIL_PATTERN.test(email.trim())) {
        setError('Email không hợp lệ.')
        return
      }
      if (password.length < 8) {
        setError('Mật khẩu phải có ít nhất 8 ký tự.')
        return
      }
      if (password !== confirm) {
        setError('Mật khẩu xác nhận không khớp.')
        return
      }

      try {
        const result = await register(email.trim(), password, name.trim() || undefined)
        if (result?.message) {
          setSuccessMsg(result.message)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Đăng ký thất bại.')
      }
    },
    [name, email, password, confirm, register]
  )

  const handleGoogle = useCallback(async () => {
    setError(null)
    try {
      await startGoogleOAuth()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không mở được Google OAuth.')
    }
  }, [startGoogleOAuth])

  if (successMsg) {
    return (
      <>
        <h2 style={{ fontSize: 18, fontWeight: 800, color: '#0f172a', marginBottom: 16 }}>
          Kiểm tra email
        </h2>
        <div style={{ ...alertSuccess, marginBottom: 20 }}>
          {successMsg}
        </div>
        <button
          onClick={onGoLogin}
          style={{
            background: 'none',
            border: 'none',
            color: '#0ea5e9',
            cursor: 'pointer',
            fontSize: 13,
            padding: 0,
          }}
        >
          ← Quay lại đăng nhập
        </button>
      </>
    )
  }

  return (
    <>
      <h2 style={{ fontSize: 18, fontWeight: 800, color: '#0f172a', marginBottom: 24 }}>
        Tạo tài khoản
      </h2>

      {!isSupabaseConfigured && (
        <div style={{ ...alertWarning, marginBottom: 16 }}>
          Supabase chưa được cấu hình. Vui lòng thêm <code>VITE_SUPABASE_URL</code> và{' '}
          <code>VITE_SUPABASE_ANON_KEY</code> vào <code>.env</code>.
        </div>
      )}

      {error && <div style={{ ...alertError, marginBottom: 16 }}>{error}</div>}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <input
          type="text"
          placeholder="Họ và tên (tùy chọn)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          autoComplete="name"
          style={inputStyle}
        />
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
          placeholder="Mật khẩu (ít nhất 8 ký tự)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          autoComplete="new-password"
          style={inputStyle}
        />
        <input
          type="password"
          placeholder="Xác nhận mật khẩu"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          required
          autoComplete="new-password"
          style={inputStyle}
        />

        <button
          type="submit"
          disabled={loading || !isSupabaseConfigured}
          style={{ ...buttonPrimary, cursor: loading || !isSupabaseConfigured ? 'not-allowed' : 'pointer', opacity: loading || !isSupabaseConfigured ? 0.7 : 1, marginTop: 4 }}
        >
          {loading ? 'Đang xử lý...' : 'Tạo tài khoản'}
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

      <div style={{ marginTop: 20, textAlign: 'center', fontSize: 13 }}>
        <button
          onClick={onGoLogin}
          style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 13, padding: 0 }}
        >
          ← Đã có tài khoản? Đăng nhập
        </button>
      </div>
    </>
  )
}
