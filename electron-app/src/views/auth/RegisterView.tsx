import { useState, useCallback } from 'react'
import { useAuthStore } from '../../store/authStore'
import { isSupabaseConfigured } from '../../lib/supabase'
import { Button, Field, Icon, Input } from '../../components/ui'
import { alertError, alertSuccess, alertWarning } from '../../styles/designTokens'

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
        if (result?.message) setSuccessMsg(result.message)
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
        <h2 style={{ fontSize: 20, fontWeight: 800, color: 'var(--color-text-main)', margin: '0 0 16px' }}>
          Kiểm tra email
        </h2>
        <div style={{ ...alertSuccess, marginBottom: 20 }}>{successMsg}</div>
        <button onClick={onGoLogin} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'none', border: 'none', color: 'var(--color-primary)', cursor: 'pointer', fontSize: 13, padding: 0, fontWeight: 700 }}>
          <Icon name="arrow_back" size={14} /> Quay lại đăng nhập
        </button>
      </>
    )
  }

  return (
    <>
      <h2 style={{ fontSize: 20, fontWeight: 800, color: 'var(--color-text-main)', margin: '0 0 6px', letterSpacing: '-0.02em' }}>
        Tạo tài khoản
      </h2>
      <p style={{ fontSize: 14, color: 'var(--color-text-muted)', margin: '0 0 24px' }}>
        Thiết lập workspace để quản lý transcript và Jira action items.
      </p>

      {!isSupabaseConfigured && (
        <div style={{ ...alertWarning, marginBottom: 16 }}>
          Supabase chưa được cấu hình. Vui lòng thêm <code>VITE_SUPABASE_URL</code> và{' '}
          <code>VITE_SUPABASE_ANON_KEY</code> vào <code>.env</code>.
        </div>
      )}

      {error && <div style={{ ...alertError, marginBottom: 16 }}>{error}</div>}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <Field label="Họ và tên">
          <Input type="text" placeholder="Nguyễn Văn A" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
        </Field>
        <Field label="Email" required>
          <Input type="email" placeholder="you@company.com" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
        </Field>
        <Field label="Mật khẩu" hint="Ít nhất 8 ký tự" required>
          <Input type="password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="new-password" />
        </Field>
        <Field label="Xác nhận mật khẩu" required>
          <Input type="password" placeholder="••••••••" value={confirm} onChange={(e) => setConfirm(e.target.value)} required autoComplete="new-password" />
        </Field>

        <Button type="submit" variant="primary" disabled={loading || !isSupabaseConfigured} style={{ width: '100%', marginTop: 4 }}>
          {loading && <Icon name="progress_activity" size={18} style={{ animation: 'spin 1s linear infinite' }} />}
          {loading ? 'Đang xử lý...' : 'Tạo tài khoản'}
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

      <div style={{ marginTop: 20, textAlign: 'center', fontSize: 13 }}>
        <button onClick={onGoLogin} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, background: 'none', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer', fontSize: 13, padding: 0 }}>
          <Icon name="arrow_back" size={14} /> Đã có tài khoản? Đăng nhập
        </button>
      </div>
    </>
  )
}


