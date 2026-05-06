import { useState, useCallback, useEffect } from 'react'

const STORAGE_KEY = 'settings:openai'

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

function loadFromStorage(): OpenAIConfig {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return EMPTY
    return { ...EMPTY, ...JSON.parse(raw) }
  } catch {
    return EMPTY
  }
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '9px 12px',
  border: '1px solid #cbd5e1',
  borderRadius: 8,
  fontSize: 13,
  outline: 'none',
  background: '#f8fafc',
  boxSizing: 'border-box',
}

export default function OpenAISettingsTab() {
  const [config, setConfig] = useState<OpenAIConfig>(EMPTY)
  const [showKey, setShowKey] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    setConfig(loadFromStorage())
  }, [])

  const handleSave = useCallback(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }, [config])

  const handleDelete = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setConfig(EMPTY)
  }, [])

  const isSaved = Boolean(loadFromStorage().apiKey)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ marginBottom: 4 }}>
        <span style={{ fontSize: 13, color: isSaved ? '#166534' : '#94a3b8', fontWeight: 600 }}>
          {isSaved ? '✓ API key đã cấu hình' : 'Chưa cấu hình API key'}
        </span>
      </div>

      <div style={{ position: 'relative' }}>
        <input
          placeholder="OpenAI API Key (sk-...)"
          type={showKey ? 'text' : 'password'}
          value={config.apiKey}
          onChange={(e) => setConfig((prev) => ({ ...prev, apiKey: e.target.value }))}
          style={{ ...inputStyle, paddingRight: 40 }}
        />
        <button
          onClick={() => setShowKey((v) => !v)}
          style={{
            position: 'absolute', right: 10, top: '50%',
            transform: 'translateY(-50%)',
            background: 'none', border: 'none', cursor: 'pointer', fontSize: 16,
          }}
        >
          {showKey ? '🙈' : '👁️'}
        </button>
      </div>

      <div>
        <label style={{ fontSize: 12, color: '#64748b', display: 'block', marginBottom: 6 }}>
          Model phân tích
        </label>
        <select
          value={config.model}
          onChange={(e) => setConfig((prev) => ({ ...prev, model: e.target.value }))}
          style={{ ...inputStyle }}
        >
          {MODELS.map((m) => (
            <option key={m.value} value={m.value}>{m.label}</option>
          ))}
        </select>
      </div>

      <div style={{ padding: '10px 12px', background: '#fef9c3', borderRadius: 8, fontSize: 12, color: '#713f12' }}>
        Prototype mode: OpenAI key được lưu plaintext trong localStorage của Electron renderer. Backend hiện vẫn dùng key trong <code>.env</code> server; bản production nên chuyển sang secure storage hoặc backend encrypted config.
      </div>

      <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
        <button
          onClick={handleSave}
          style={{
            padding: '9px 20px',
            background: saved ? '#22c55e' : '#0ea5e9',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            fontWeight: 600,
            fontSize: 13,
            cursor: 'pointer',
            transition: 'background 0.2s',
          }}
        >
          {saved ? '✓ Đã lưu' : '💾 Lưu'}
        </button>
        <button
          onClick={handleDelete}
          style={{
            padding: '9px 20px',
            background: '#fff',
            color: '#ef4444',
            border: '1px solid #fca5a5',
            borderRadius: 8,
            fontWeight: 600,
            fontSize: 13,
            cursor: 'pointer',
          }}
        >
          🗑️ Xóa
        </button>
      </div>
    </div>
  )
}
