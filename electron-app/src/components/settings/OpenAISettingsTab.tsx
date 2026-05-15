import { useCallback, useState } from 'react'
import { useDeleteProviderConfig, useProviderConfigStatus, useSaveProviderConfig } from '../../hooks/useProviderSettings'
import { alertError, alertSuccess, alertWarning } from '../../styles/designTokens'
import { Badge, Button, Field, Icon, Input, Select } from '../ui'

const MODELS = [
  { value: 'gpt-4o', label: 'GPT-4o' },
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
  { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
]

interface OpenAIConfig { apiKey: string; model: string }
const EMPTY: OpenAIConfig = { apiKey: '', model: 'gpt-4o' }

export default function OpenAISettingsTab() {
  const [config, setConfig] = useState<OpenAIConfig>(EMPTY)
  const [showKey, setShowKey] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const statusQuery = useProviderConfigStatus('openai')
  const saveMutation = useSaveProviderConfig('openai')
  const deleteMutation = useDeleteProviderConfig('openai')
  const configured = Boolean(statusQuery.data?.is_configured)
  const loading = statusQuery.isLoading || saveMutation.isPending || deleteMutation.isPending

  const handleSave = useCallback(async () => {
    setError(null); setSaved(false)
    if (!config.apiKey.trim()) { setError('Vui lòng nhập OpenAI API key.'); return }
    try { await saveMutation.mutateAsync({ apiKey: config.apiKey, model: config.model }); setConfig(EMPTY); setSaved(true); window.setTimeout(() => setSaved(false), 2000) }
    catch (err) { setError(err instanceof Error ? err.message : 'Không lưu được OpenAI settings.') }
  }, [config, saveMutation])

  const handleDelete = useCallback(async () => {
    setError(null); setSaved(false)
    try { await deleteMutation.mutateAsync(); setConfig(EMPTY) } catch (err) { setError(err instanceof Error ? err.message : 'Không xóa được OpenAI settings.') }
  }, [deleteMutation])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <Badge variant={configured ? 'success' : 'default'} dot>{configured ? 'Đã kết nối' : 'Chưa cấu hình API key'}</Badge>
        {configured && statusQuery.data?.masked_key && <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>{statusQuery.data.masked_key}</span>}
      </div>
      {statusQuery.error && <div style={alertError}>{statusQuery.error.message}</div>}
      {error && <div style={alertError}>{error}</div>}
      {saved && <div style={alertSuccess}>Đã lưu cấu hình OpenAI.</div>}
      <Field label="OpenAI API Key" required>
        <div style={{ position: 'relative' }}>
          <Input placeholder={configured ? 'OpenAI API Key mới' : 'OpenAI API Key (sk-...)'} type={showKey ? 'text' : 'password'} value={config.apiKey} onChange={(e) => setConfig((prev) => ({ ...prev, apiKey: e.target.value }))} style={{ paddingRight: 58 }} />
          <button onClick={() => setShowKey((v) => !v)} style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: 'var(--color-text-muted)' }}>{showKey ? 'Ẩn' : 'Hiện'}</button>
        </div>
      </Field>
      <Field label="Model phân tích">
        <Select value={config.model} onChange={(e) => setConfig((prev) => ({ ...prev, model: e.target.value }))}>
          {MODELS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
        </Select>
      </Field>
      <div style={alertWarning}>API key được lưu encrypted trên server. Form không hiển thị lại key gốc sau khi lưu.</div>
      <div style={{ display: 'flex', gap: 10, marginTop: 8, flexWrap: 'wrap' }}>
        <Button onClick={handleSave} disabled={loading} variant="primary"><Icon name={loading ? 'progress_activity' : 'cloud_sync'} size={18} style={loading ? { animation: 'spin 1s linear infinite' } : undefined} />{loading ? 'Đang xử lý...' : 'Lưu'}</Button>
        <Button onClick={handleDelete} disabled={loading || !configured} variant="danger">Xóa</Button>
        <Button disabled variant="secondary" title="Chờ backend endpoint validate">Validate key</Button>
      </div>
    </div>
  )
}
