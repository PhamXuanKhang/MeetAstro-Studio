import { useCallback, useState } from 'react'
import { useDeleteProviderConfig, useProviderConfigStatus, useSaveProviderConfig } from '../../hooks/useProviderSettings'
import { alertError, alertSuccess, alertWarning, buttonDanger, buttonDisabled, buttonPrimary, buttonSecondary, colors, inputStyle } from '../../styles/designTokens'

interface JiraConfig {
  url: string
  email: string
  token: string
  projectKey: string
}

const EMPTY: JiraConfig = { url: '', email: '', token: '', projectKey: '' }

interface Props {
  onSaved?: () => void
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

  const set = (key: keyof JiraConfig) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setConfig((prev) => ({ ...prev, [key]: e.target.value }))

  const handleSave = useCallback(async () => {
    setError(null)
    setSaved(false)
    if (!config.url.trim() || !config.email.trim() || !config.token.trim() || !config.projectKey.trim()) {
      setError('Vui lòng nhập đủ URL, email, token và project key.')
      return
    }

    try {
      await saveMutation.mutateAsync({
        url: config.url.trim(),
        email: config.email.trim(),
        token: config.token,
        projectKey: config.projectKey.trim(),
      })
      setConfig(EMPTY)
      setSaved(true)
      window.setTimeout(() => setSaved(false), 2000)
      onSaved?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không lưu được Jira settings.')
    }
  }, [config, onSaved, saveMutation])

  const handleDelete = useCallback(async () => {
    setError(null)
    setSaved(false)
    try {
      await deleteMutation.mutateAsync()
      setConfig(EMPTY)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không xóa được Jira settings.')
    }
  }, [deleteMutation])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ marginBottom: 4 }}>
        <span style={{ fontSize: 13, color: configured ? colors.success : '#94a3b8', fontWeight: 600 }}>
          {configured ? 'Đã kết nối' : 'Chưa cấu hình'}
        </span>
        {configured && statusQuery.data?.masked_key && (
          <span style={{ marginLeft: 8, fontSize: 12, color: '#64748b' }}>
            {statusQuery.data.masked_key}
          </span>
        )}
      </div>

      {statusQuery.error && <div style={alertError}>{statusQuery.error.message}</div>}
      {error && <div style={alertError}>{error}</div>}
      {saved && <div style={alertSuccess}>Đã lưu cấu hình Jira.</div>}

      <input placeholder="Base URL (https://yourco.atlassian.net)" value={config.url} onChange={set('url')} style={inputStyle} />
      <input placeholder="Email" type="email" value={config.email} onChange={set('email')} style={inputStyle} />
      <div style={{ position: 'relative' }}>
        <input
          placeholder={configured ? 'API Token mới' : 'API Token'}
          type={showToken ? 'text' : 'password'}
          value={config.token}
          onChange={set('token')}
          style={{ ...inputStyle, paddingRight: 40 }}
        />
        <button
          onClick={() => setShowToken((v) => !v)}
          style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 13 }}
        >
          {showToken ? 'Ẩn' : 'Hiện'}
        </button>
      </div>
      <input placeholder="Project Key (ví dụ: PROJ)" value={config.projectKey} onChange={set('projectKey')} style={inputStyle} />

      <div style={alertWarning}>Credentials được lưu encrypted trên server. Form không hiển thị lại token gốc sau khi lưu.</div>

      <div style={{ display: 'flex', gap: 10, marginTop: 8, flexWrap: 'wrap' }}>
        <button onClick={handleSave} disabled={loading} style={{ ...buttonPrimary, ...(loading ? buttonDisabled : {}) }}>
          {loading ? 'Đang xử lý...' : 'Lưu cấu hình'}
        </button>
        <button onClick={handleDelete} disabled={loading || !configured} style={{ ...buttonDanger, ...((loading || !configured) ? buttonDisabled : {}) }}>
          Xóa
        </button>
        <button disabled style={{ ...buttonSecondary, ...buttonDisabled }} title="Chờ backend endpoint test-connection">
          Test connection
        </button>
      </div>
    </div>
  )
}
