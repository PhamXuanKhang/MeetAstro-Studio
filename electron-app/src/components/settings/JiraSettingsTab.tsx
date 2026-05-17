import { useCallback, useState } from 'react'
import type { CSSProperties } from 'react'
import { useDeleteProviderConfig, useProviderConfigStatus, useSaveProviderConfig } from '../../hooks/useProviderSettings'
import { alertError, alertSuccess, alertWarning } from '../../styles/designTokens'
import { Badge, Button, Field, Icon, Input } from '../ui'

interface JiraConfig { url: string; email: string; token: string; projectKey: string }
const EMPTY: JiraConfig = { url: '', email: '', token: '', projectKey: '' }
interface Props { onSaved?: () => void }

const ATLASSIAN_API_TOKEN_URL = 'https://id.atlassian.com/manage-profile/security/api-tokens'
const ATLASSIAN_API_TOKEN_HELP_URL = 'https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/'

const guideCardStyle: CSSProperties = {
  padding: 14,
  borderRadius: 'var(--radius-brand)',
  border: '1px solid var(--color-border-subtle)',
  background: 'var(--color-bg)',
}

const guideLinkStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
  color: 'var(--color-primary)',
  fontSize: 13,
  fontWeight: 700,
  textDecoration: 'none',
}

const inlineCodeStyle: CSSProperties = {
  padding: '1px 5px',
  borderRadius: 4,
  background: 'var(--color-surface-2)',
  color: 'var(--color-text-main)',
  fontSize: 12,
}

export default function JiraSettingsTab({ onSaved }: Props) {
  const [config, setConfig] = useState<JiraConfig>(EMPTY)
  const [showToken, setShowToken] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const statusQuery = useProviderConfigStatus('jira')
  const saveMutation = useSaveProviderConfig('jira')
  const deleteMutation = useDeleteProviderConfig('jira')
  const configured = Boolean(statusQuery.data?.is_configured)
  const loading = statusQuery.isLoading || saveMutation.isPending || deleteMutation.isPending
  const set = (key: keyof JiraConfig) => (e: React.ChangeEvent<HTMLInputElement>) => setConfig((prev) => ({ ...prev, [key]: e.target.value }))

  const handleSave = useCallback(async () => {
    setError(null); setSaved(false)
    if (!config.url.trim() || !config.email.trim() || !config.token.trim() || !config.projectKey.trim()) { setError('Vui lòng nhập đủ URL, email, token và project key.'); return }
    try {
      await saveMutation.mutateAsync({ url: config.url.trim(), email: config.email.trim(), token: config.token, projectKey: config.projectKey.trim() })
      setConfig(EMPTY); setSaved(true); window.setTimeout(() => setSaved(false), 2000); onSaved?.()
    } catch (err) { setError(err instanceof Error ? err.message : 'Không lưu được Jira settings.') }
  }, [config, onSaved, saveMutation])

  const handleDelete = useCallback(async () => {
    setError(null); setSaved(false)
    try { await deleteMutation.mutateAsync(); setConfig(EMPTY) } catch (err) { setError(err instanceof Error ? err.message : 'Không xóa được Jira settings.') }
  }, [deleteMutation])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <Badge variant={configured ? 'success' : 'default'} dot>{configured ? 'Đã kết nối' : 'Chưa cấu hình'}</Badge>
        {configured && statusQuery.data?.masked_key && <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>{statusQuery.data.masked_key}</span>}
      </div>
      {statusQuery.error && <div style={alertError}>{statusQuery.error.message}</div>}
      {error && <div style={alertError}>{error}</div>}
      {saved && <div style={alertSuccess}>Đã lưu cấu hình Jira.</div>}
      <div style={guideCardStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10, color: 'var(--color-text-main)', fontWeight: 700 }}>
          <Icon name="help" size={18} />
          Cách lấy thông tin Jira
        </div>
        <ol style={{ margin: 0, paddingLeft: 20, color: 'var(--color-text-muted)', fontSize: 13, lineHeight: 1.55 }}>
          <li><strong style={{ color: 'var(--color-text-main)' }}>Base URL:</strong> mở Jira trên trình duyệt và copy phần đầu địa chỉ, ví dụ <code style={inlineCodeStyle}>https://yourco.atlassian.net</code>.</li>
          <li><strong style={{ color: 'var(--color-text-main)' }}>Email:</strong> dùng email bạn đăng nhập vào Jira/Atlassian.</li>
          <li><strong style={{ color: 'var(--color-text-main)' }}>API Token:</strong> bấm link bên dưới để tạo token, đặt tên dễ nhớ, copy token và dán vào ô này. Đây không phải mật khẩu đăng nhập Jira.</li>
          <li><strong style={{ color: 'var(--color-text-main)' }}>Project Key:</strong> mở một issue trong dự án. Nếu URL hoặc mã issue là <code style={inlineCodeStyle}>PROJ-123</code> thì project key là <code style={inlineCodeStyle}>PROJ</code>.</li>
        </ol>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 14, marginTop: 12 }}>
          <a href={ATLASSIAN_API_TOKEN_URL} target="_blank" rel="noreferrer" style={guideLinkStyle}>
            <Icon name="open_in_new" size={16} />
            Tạo API token
          </a>
          <a href={ATLASSIAN_API_TOKEN_HELP_URL} target="_blank" rel="noreferrer" style={guideLinkStyle}>
            <Icon name="article" size={16} />
            Hướng dẫn của Atlassian
          </a>
        </div>
      </div>
      <Field label="Base URL" required hint="Thường có dạng https://ten-cong-ty.atlassian.net. Nếu công ty dùng Jira nội bộ, copy đúng địa chỉ Jira bạn đang mở."><Input placeholder="https://yourco.atlassian.net" value={config.url} onChange={set('url')} /></Field>
      <Field label="Email" required hint="Email tài khoản Atlassian/Jira có quyền tạo issue trong dự án cần đồng bộ."><Input placeholder="name@company.com" type="email" value={config.email} onChange={set('email')} /></Field>
      <Field label="API Token" required>
        <div style={{ position: 'relative' }}>
          <Input placeholder={configured ? 'API Token mới' : 'API Token'} type={showToken ? 'text' : 'password'} value={config.token} onChange={set('token')} style={{ paddingRight: 58 }} />
          <button onClick={() => setShowToken((v) => !v)} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: 'var(--color-text-muted)' }}>{showToken ? 'Ẩn' : 'Hiện'}</button>
        </div>
        <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>Tạo tại Atlassian Account &gt; Security &gt; API tokens. Token chỉ hiện một lần sau khi tạo.</span>
      </Field>
      <Field label="Project Key" required hint="Lấy phần chữ đứng trước dấu gạch trong mã issue, ví dụ PROJ trong PROJ-123."><Input placeholder="PROJ" value={config.projectKey} onChange={set('projectKey')} /></Field>
      <div style={alertWarning}>Credentials được lưu encrypted trên server. Form không hiển thị lại token gốc sau khi lưu.</div>
      <div style={{ display: 'flex', gap: 10, marginTop: 8, flexWrap: 'wrap' }}>
        <Button onClick={handleSave} disabled={loading} variant="primary"><Icon name={loading ? 'progress_activity' : 'cloud_sync'} size={18} style={loading ? { animation: 'spin 1s linear infinite' } : undefined} />{loading ? 'Đang xử lý...' : 'Lưu cấu hình'}</Button>
        <Button onClick={handleDelete} disabled={loading || !configured} variant="danger">Xóa</Button>
        <Button disabled variant="secondary" title="Chờ backend endpoint test-connection">Test connection</Button>
      </div>
    </div>
  )
}
