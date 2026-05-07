import { useCallback, useState } from 'react'
import { useAuthStore } from '../../store/authStore'
import { alertError, alertSuccess, buttonPrimary, inputStyle } from '../../styles/designTokens'

interface Props {
  onDone: () => void
}

export default function ResetPasswordView({ onDone }: Props) {
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const { updatePassword, loading } = useAuthStore()

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault()
      setError(null)
      if (password.length < 8) {
        setError('Mật khẩu phải có ít nhất 8 ký tự.')
        return
      }
      if (password !== confirm) {
        setError('Mật khẩu xác nhận không khớp.')
        return
      }

      try {
        await updatePassword(password)
        setSuccess(true)
        window.setTimeout(onDone, 1000)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Không cập nhật được mật khẩu.')
      }
    },
    [confirm, onDone, password, updatePassword]
  )

  return (
    <>
      <h2 style={{ fontSize: 18, fontWeight: 800, color: '#0f172a', marginBottom: 8 }}>
        Đặt lại mật khẩu
      </h2>
      <p style={{ fontSize: 13, color: '#64748b', marginBottom: 20 }}>
        Nhập mật khẩu mới cho tài khoản của bạn.
      </p>

      {error && <div style={{ ...alertError, marginBottom: 16 }}>{error}</div>}
      {success && <div style={{ ...alertSuccess, marginBottom: 16 }}>Đã cập nhật mật khẩu.</div>}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <input
          type="password"
          placeholder="Mật khẩu mới"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="new-password"
          style={inputStyle}
        />
        <input
          type="password"
          placeholder="Xác nhận mật khẩu mới"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          autoComplete="new-password"
          style={inputStyle}
        />
        <button
          type="submit"
          disabled={loading}
          style={{ ...buttonPrimary, opacity: loading ? 0.7 : 1, cursor: loading ? 'not-allowed' : 'pointer' }}
        >
          {loading ? 'Đang cập nhật...' : 'Cập nhật mật khẩu'}
        </button>
      </form>
    </>
  )
}
