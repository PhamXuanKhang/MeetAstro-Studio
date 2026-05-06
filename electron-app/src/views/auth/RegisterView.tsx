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

export default function RegisterView({ onGoLogin }: Props) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)
  const { register, loading } = useAuthStore()

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      setError(null)
      setSuccessMsg(null)

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

  if (successMsg) {
    return (
      <>
        <h2 style={{ fontSize: 18, fontWeight: 800, color: '#0f172a', marginBottom: 16 }}>
          Kiểm tra email
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
          {loading ? 'Đang xử lý...' : 'Tạo tài khoản'}
        </button>
      </form>

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
