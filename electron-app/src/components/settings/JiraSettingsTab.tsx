import { useState, useCallback, useEffect } from 'react'

const STORAGE_KEY = 'settings:jira'

interface JiraConfig {
  url: string
  email: string
  token: string
  projectKey: string
}

const EMPTY: JiraConfig = { url: '', email: '', token: '', projectKey: '' }

function loadFromStorage(): JiraConfig {
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

interface Props {
  onSaved?: () => void
}

export default function JiraSettingsTab({ onSaved }: Props) {
  const [config, setConfig] = useState<JiraConfig>(EMPTY)
  const [showToken, setShowToken] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    setConfig(loadFromStorage())
  }, [])

  const set = (key: keyof JiraConfig) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setConfig((prev) => ({ ...prev, [key]: e.target.value }))

  const handleSave = useCallback(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
    onSaved?.()
  }, [config, onSaved])

  const handleDelete = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setConfig(EMPTY)
    setSaved(false)
  }, [])

  const isSaved = Boolean(loadFromStorage().url || loadFromStorage().token)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ marginBottom: 4 }}>
        <span style={{ fontSize: 13, color: isSaved ? '#166534' : '#94a3b8', fontWeight: 600 }}>
          {isSaved ? '✓ Đã cấu hình' : 'Chưa cấu hình'}
        </span>
      </div>

      <input
        placeholder="Base URL (https://yourco.atlassian.net)"
        value={config.url}
        onChange={set('url')}
        style={inputStyle}
      />
      <input
        placeholder="Email"
        type="email"
        value={config.email}
        onChange={set('email')}
        style={inputStyle}
      />
      <div style={{ position: 'relative' }}>
        <input
          placeholder="API Token"
          type={showToken ? 'text' : 'password'}
          value={config.token}
          onChange={set('token')}
          style={{ ...inputStyle, paddingRight: 40 }}
        />
        <button
          onClick={() => setShowToken((v) => !v)}
          style={{
            position: 'absolute', right: 10, top: '50%',
            transform: 'translateY(-50%)',
            background: 'none', border: 'none', cursor: 'pointer', fontSize: 16,
          }}
        >
          {showToken ? '🙈' : '👁️'}
        </button>
      </div>
      <input
        placeholder="Project Key (ví dụ: PROJ)"
        value={config.projectKey}
        onChange={set('projectKey')}
        style={inputStyle}
      />

      <div style={{ padding: '10px 12px', background: '#fef9c3', borderRadius: 8, fontSize: 12, color: '#713f12' }}>
        Prototype mode: Jira token được lưu plaintext trong localStorage của Electron renderer. Chỉ dùng cho môi trường dev/demo; bản production nên chuyển sang secure storage hoặc backend encrypted config.
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
          {saved ? '✓ Đã lưu' : '💾 Lưu cấu hình'}
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
        <button
          disabled
          style={{
            padding: '9px 20px',
            background: '#f1f5f9',
            color: '#94a3b8',
            border: '1px solid #e2e8f0',
            borderRadius: 8,
            fontWeight: 600,
            fontSize: 13,
            cursor: 'not-allowed',
          }}
          title="Tính năng sẽ có sau khi backend sẵn sàng"
        >
          🔗 Test connection
        </button>
      </div>
    </div>
  )
}
