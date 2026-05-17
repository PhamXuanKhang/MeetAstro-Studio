import { useCallback, useState } from 'react'
import { useAuthStore } from '../../store/authStore'
import { Button, Field, Icon, Input } from '../../components/ui'
import { alertError, alertSuccess } from '../../styles/designTokens'

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
      <h2 style={{ fontSize: 20, fontWeight: 800, color: 'var(--color-text-main)', margin: '0 0 8px' }}>
        Đặt lại mật khẩu
      </h2>
      <p style={{ fontSize: 14, color: 'var(--color-text-muted)', margin: '0 0 20px', lineHeight: 1.6 }}>
        Nhập mật khẩu mới cho tài khoản của bạn.
      </p>

      {error && <div style={{ ...alertError, marginBottom: 16 }}>{error}</div>}
      {success && <div style={{ ...alertSuccess, marginBottom: 16 }}>Đã cập nhật mật khẩu.</div>}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <Field label="Mật khẩu mới" hint="Ít nhất 8 ký tự" required>
          <Input type="password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
        </Field>
        <Field label="Xác nhận mật khẩu mới" required>
          <Input type="password" placeholder="••••••••" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" />
        </Field>
        <Button type="submit" variant="primary" disabled={loading} style={{ width: '100%' }}>
          {loading && <Icon name="progress_activity" size={18} style={{ animation: 'spin 1s linear infinite' }} />}
          {loading ? 'Đang cập nhật...' : 'Cập nhật mật khẩu'}
        </Button>
      </form>
    </>
  )
}
