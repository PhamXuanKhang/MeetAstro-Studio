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
  onGoRegister: () => void
  onGoForgot: () => void
}

export default function LoginView({ onGoRegister, onGoForgot }: Props) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const { login, loading } = useAuthStore()

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      setError(null)
      try {
        await login(email.trim(), password)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Đăng nhập thất bại.')
      }
    },
    [email, password, login]
  )

  return (
    <>
      <h2 style={{ fontSize: 18, fontWeight: 800, color: '#0f172a', marginBottom: 24 }}>
        Đăng nhập
      </h2>

      {!isSupabaseConfigured && (
        <div
          style={{
            marginBottom: 16,
            padding: '10px 14px',
            background: '#fef9c3',
            borderRadius: 8,
            fontSize: 12,
            color: '#713f12',
            border: '1px solid #fde68a',
          }}
        >
          Supabase chưa được cấu hình. Vui lòng thêm{' '}
          <code>VITE_SUPABASE_URL</code> và <code>VITE_SUPABASE_ANON_KEY</code> vào{' '}
          <code>.env</code>.
        </div>
      )}

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
          {loading ? 'Đang đăng nhập...' : 'Đăng nhập'}
        </button>
      </form>

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
