import { useCallback, useEffect, useState } from 'react'
import { deleteProviderConfig, listProviderConfigs, setProviderConfig } from '../../api/settings'
import { alertError, alertSuccess, alertWarning, buttonDanger, buttonDisabled, buttonPrimary, buttonSecondary, colors, inputStyle } from '../../styles/designTokens'

const MODELS = [
  { value: 'gpt-4o', label: 'GPT-4o (khuyến nghị)' },
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini (nhanh hơn)' },
  { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
]

interface OpenAIConfig {
  apiKey: string
  model: string
}

const EMPTY: OpenAIConfig = { apiKey: '', model: 'gpt-4o' }

export default function OpenAISettingsTab() {
  const [config, setConfig] = useState<OpenAIConfig>(EMPTY)
  const [showKey, setShowKey] = useState(false)
  const [configured, setConfigured] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    let alive = true
    setLoading(true)
    listProviderConfigs()
      .then((providers) => {
        if (alive) setConfigured(providers.includes('openai'))
      })
      .catch((err) => {
        if (alive) setError(err instanceof Error ? err.message : 'Không tải được trạng thái OpenAI.')
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [])

  const handleSave = useCallback(async () => {
    setError(null)
    setSaved(false)
    if (!config.apiKey.trim()) {
      setError('Vui lòng nhập OpenAI API key.')
      return
    }

    setLoading(true)
    try {
      await setProviderConfig('openai', { apiKey: config.apiKey, model: config.model })
      setConfigured(true)
      setConfig(EMPTY)
      setSaved(true)
      window.setTimeout(() => setSaved(false), 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không lưu được OpenAI settings.')
    } finally {
      setLoading(false)
    }
  }, [config])

  const handleDelete = useCallback(async () => {
    setError(null)
    setSaved(false)
    setLoading(true)
    try {
      await deleteProviderConfig('openai')
      setConfigured(false)
      setConfig(EMPTY)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không xóa được OpenAI settings.')
    } finally {
      setLoading(false)
    }
  }, [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ marginBottom: 4 }}>
        <span style={{ fontSize: 13, color: configured ? colors.success : '#94a3b8', fontWeight: 600 }}>
          {configured ? 'API key đã cấu hình trên server' : 'Chưa cấu hình API key'}
        </span>
      </div>

      {error && <div style={alertError}>{error}</div>}
      {saved && <div style={alertSuccess}>Đã lưu cấu hình OpenAI.</div>}

      <div style={{ position: 'relative' }}>
        <input
          placeholder={configured ? 'OpenAI API Key mới (để trống nếu không lưu lại)' : 'OpenAI API Key (sk-...)'}
          type={showKey ? 'text' : 'password'}
          value={config.apiKey}
          onChange={(e) => setConfig((prev) => ({ ...prev, apiKey: e.target.value }))}
          style={{ ...inputStyle, paddingRight: 48 }}
        />
        <button
          onClick={() => setShowKey((v) => !v)}
          style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 13 }}
        >
          {showKey ? 'Ẩn' : 'Hiện'}
        </button>
      </div>

      <div>
        <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 6 }}>Model phân tích</label>
        <select value={config.model} onChange={(e) => setConfig((prev) => ({ ...prev, model: e.target.value }))} style={inputStyle}>
          {MODELS.map((m) => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </select>
      </div>

      <div style={alertWarning}>API key được lưu encrypted trên server. Backend hiện chưa có endpoint validate key, nên nút kiểm tra đang bị tắt.</div>

      <div style={{ display: 'flex', gap: 10, marginTop: 8, flexWrap: 'wrap' }}>
        <button onClick={handleSave} disabled={loading} style={{ ...buttonPrimary, ...(loading ? buttonDisabled : {}) }}>
          {loading ? 'Đang xử lý...' : 'Lưu'}
        </button>
        <button onClick={handleDelete} disabled={loading || !configured} style={{ ...buttonDanger, ...((loading || !configured) ? buttonDisabled : {}) }}>
          Xóa
        </button>
        <button disabled style={{ ...buttonSecondary, ...buttonDisabled }} title="Chờ backend endpoint validate">
          Validate key
        </button>
      </div>
    </div>
  )
}
