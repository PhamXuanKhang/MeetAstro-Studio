import { useState, useCallback, useEffect } from 'react'
import { listProviderConfigs, setProviderConfig, deleteProviderConfig } from '../api/settings'

const PROVIDERS = ['jira', 'trello', 'notion', 'slack', 'teams']

function Toast({ msg, isError, onClose }: { msg: string; isError: boolean; onClose: () => void }) {
  useEffect(() => {
    const t = setTimeout(onClose, 3000)
    return () => clearTimeout(t)
  }, [onClose])
  return (
    <div style={{
      position: 'fixed', bottom: 24, right: 24, zIndex: 999,
      padding: '12px 20px', borderRadius: 10,
      background: isError ? '#fee2e2' : '#dcfce7',
      color: isError ? '#991b1b' : '#166534',
      boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
      fontSize: 13, fontWeight: 500,
    }}>
      {msg}
    </div>
  )
}

export default function SettingsView() {
  const [selectedProvider, setSelectedProvider] = useState('jira')
  const [configuredProviders, setConfiguredProviders] = useState<string[]>([])
  const [toast, setToast] = useState<{ msg: string; isError: boolean } | null>(null)
  const [loading, setLoading] = useState(false)

  // Jira fields
  const [jiraUrl, setJiraUrl] = useState('')
  const [jiraEmail, setJiraEmail] = useState('')
  const [jiraToken, setJiraToken] = useState('')
  const [jiraProject, setJiraProject] = useState('')
  // Generic JSON field
  const [genericJson, setGenericJson] = useState('')
  const [showToken, setShowToken] = useState(false)

  const showToast = useCallback((msg: string, isError = false) => {
    setToast({ msg, isError })
  }, [])

  const refreshStatus = useCallback(async () => {
    try {
      const providers = await listProviderConfigs()
      setConfiguredProviders(providers)
    } catch (e) {
      showToast(`Lỗi: ${e instanceof Error ? e.message : e}`, true)
    }
  }, [showToast])

  useEffect(() => {
    refreshStatus()
  }, [refreshStatus])

  const isConfigured = configuredProviders.includes(selectedProvider)

  const handleSave = useCallback(async () => {
    setLoading(true)
    try {
      let cfg: Record<string, string>
      if (selectedProvider === 'jira') {
        cfg = {}
        if (jiraUrl.trim()) cfg.url = jiraUrl.trim()
        if (jiraEmail.trim()) cfg.email = jiraEmail.trim()
        if (jiraToken.trim()) cfg.token = jiraToken.trim()
        if (jiraProject.trim()) cfg.project_key = jiraProject.trim()
        if (Object.keys(cfg).length === 0) {
          showToast('Vui lòng điền ít nhất một trường.', true)
          return
        }
      } else {
        const raw = genericJson.trim()
        if (!raw) { showToast('Vui lòng nhập JSON config.', true); return }
        try {
          const parsed = JSON.parse(raw)
          if (typeof parsed !== 'object' || Array.isArray(parsed)) {
            showToast('JSON phải là object { key: value }.', true); return
          }
          cfg = parsed
        } catch {
          showToast('JSON không hợp lệ.', true); return
        }
      }
      await setProviderConfig(selectedProvider, cfg)
      showToast(`Đã lưu cấu hình ${selectedProvider}.`)
      await refreshStatus()
    } catch (e) {
      showToast(`Lỗi: ${e instanceof Error ? e.message : e}`, true)
    } finally {
      setLoading(false)
    }
  }, [selectedProvider, jiraUrl, jiraEmail, jiraToken, jiraProject, genericJson, showToast, refreshStatus])

  const handleDelete = useCallback(async () => {
    try {
      await deleteProviderConfig(selectedProvider)
      showToast(`Đã xóa cấu hình ${selectedProvider}.`)
      await refreshStatus()
    } catch (e) {
      showToast(`Lỗi: ${e instanceof Error ? e.message : e}`, true)
    }
  }, [selectedProvider, showToast, refreshStatus])

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '9px 12px', border: '1px solid #cbd5e1',
    borderRadius: 8, fontSize: 13, outline: 'none', background: '#f8fafc',
  }

  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      {toast && <Toast msg={toast.msg} isError={toast.isError} onClose={() => setToast(null)} />}

      <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #e2e8f0', padding: 24 }}>
        <h2 style={{ fontSize: 18, fontWeight: 800, marginBottom: 20, color: '#0f172a' }}>
          Integrations
        </h2>

        {/* Provider selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
          <label style={{ fontSize: 13, color: '#64748b', width: 70 }}>Provider</label>
          <select
            value={selectedProvider}
            onChange={(e) => setSelectedProvider(e.target.value)}
            style={{ ...inputStyle, width: 160 }}
          >
            {PROVIDERS.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          <span style={{
            fontSize: 12, fontWeight: 600,
            color: isConfigured ? '#166534' : '#94a3b8',
          }}>
            {isConfigured ? `✓ ${selectedProvider} configured` : `${selectedProvider} not configured`}
          </span>
        </div>

        <hr style={{ border: 'none', borderTop: '1px solid #e2e8f0', margin: '16px 0' }} />

        {/* Form */}
        {selectedProvider === 'jira' ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <input placeholder="Base URL (https://yourco.atlassian.net)" value={jiraUrl} onChange={(e) => setJiraUrl(e.target.value)} style={inputStyle} />
            <input placeholder="Email" value={jiraEmail} onChange={(e) => setJiraEmail(e.target.value)} style={inputStyle} />
            <div style={{ position: 'relative' }}>
              <input
                placeholder="API Token"
                type={showToken ? 'text' : 'password'}
                value={jiraToken}
                onChange={(e) => setJiraToken(e.target.value)}
                style={{ ...inputStyle, paddingRight: 40 }}
              />
              <button
                onClick={() => setShowToken((v) => !v)}
                style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 16 }}
              >
                {showToken ? '🙈' : '👁️'}
              </button>
            </div>
            <input placeholder="Project Key (PROJ)" value={jiraProject} onChange={(e) => setJiraProject(e.target.value)} style={inputStyle} />
          </div>
        ) : (
          <textarea
            placeholder={`Config JSON cho ${selectedProvider}\n{"token": "...", "workspace": "..."}`}
            value={genericJson}
            onChange={(e) => setGenericJson(e.target.value)}
            rows={5}
            style={{ ...inputStyle, resize: 'vertical', fontFamily: 'monospace' }}
          />
        )}

        <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
          <button
            onClick={handleSave}
            disabled={loading}
            style={{
              padding: '9px 20px', background: '#0ea5e9', color: '#fff', border: 'none',
              borderRadius: 8, fontWeight: 600, fontSize: 13, cursor: 'pointer',
              opacity: loading ? 0.7 : 1,
            }}
          >
            💾 {loading ? 'Đang lưu...' : 'Lưu cấu hình'}
          </button>
          <button
            onClick={handleDelete}
            style={{
              padding: '9px 20px', background: '#fff', color: '#ef4444',
              border: '1px solid #fca5a5', borderRadius: 8, fontWeight: 600, fontSize: 13, cursor: 'pointer',
            }}
          >
            🗑️ Xóa cấu hình
          </button>
        </div>
      </div>
    </div>
  )
}
