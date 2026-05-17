import { useCallback, useState } from 'react'
import { useDeleteProviderConfig, useProviderConfigStatus, useSaveProviderConfig } from '../../hooks/useProviderSettings'
import { alertError, alertSuccess, alertWarning } from '../../styles/designTokens'
import { Badge, Button, Field, Icon, Input } from '../ui'

interface JiraConfig { url: string; email: string; token: string; projectKey: string }
const EMPTY: JiraConfig = { url: '', email: '', token: '', projectKey: '' }
interface Props { onSaved?: () => void }

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
      <Field label="Base URL" required><Input placeholder="https://yourco.atlassian.net" value={config.url} onChange={set('url')} /></Field>
      <Field label="Email" required><Input placeholder="name@company.com" type="email" value={config.email} onChange={set('email')} /></Field>
      <Field label="API Token" required>
        <div style={{ position: 'relative' }}>
          <Input placeholder={configured ? 'API Token mới' : 'API Token'} type={showToken ? 'text' : 'password'} value={config.token} onChange={set('token')} style={{ paddingRight: 58 }} />
          <button onClick={() => setShowToken((v) => !v)} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: 'var(--color-text-muted)' }}>{showToken ? 'Ẩn' : 'Hiện'}</button>
        </div>
      </Field>
      <Field label="Project Key" required><Input placeholder="PROJ" value={config.projectKey} onChange={set('projectKey')} /></Field>
      <div style={alertWarning}>Credentials được lưu encrypted trên server. Form không hiển thị lại token gốc sau khi lưu.</div>
      <div style={{ display: 'flex', gap: 10, marginTop: 8, flexWrap: 'wrap' }}>
        <Button onClick={handleSave} disabled={loading} variant="primary"><Icon name={loading ? 'progress_activity' : 'cloud_sync'} size={18} style={loading ? { animation: 'spin 1s linear infinite' } : undefined} />{loading ? 'Đang xử lý...' : 'Lưu cấu hình'}</Button>
        <Button onClick={handleDelete} disabled={loading || !configured} variant="danger">Xóa</Button>
        <Button disabled variant="secondary" title="Chờ backend endpoint test-connection">Test connection</Button>
      </div>
    </div>
  )
}
