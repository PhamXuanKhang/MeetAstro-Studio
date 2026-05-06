import { useState } from 'react'
import JiraSettingsTab from '../components/settings/JiraSettingsTab'
import OpenAISettingsTab from '../components/settings/OpenAISettingsTab'

type Tab = 'jira' | 'openai'

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'jira', label: 'Jira', icon: '📋' },
  { id: 'openai', label: 'OpenAI', icon: '🤖' },
]

export default function SettingsView() {
  const [activeTab, setActiveTab] = useState<Tab>('jira')

  return (
    <div style={{ maxWidth: 600, margin: '0 auto' }}>
      <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #e2e8f0', overflow: 'hidden' }}>
        {/* Tab header */}
        <div style={{ display: 'flex', borderBottom: '1px solid #e2e8f0' }}>
          {TABS.map((tab) => {
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  flex: 1,
                  padding: '14px 20px',
                  background: isActive ? '#fff' : '#f8fafc',
                  border: 'none',
                  borderBottom: isActive ? '2px solid #0ea5e9' : '2px solid transparent',
                  cursor: 'pointer',
                  fontSize: 14,
                  fontWeight: isActive ? 700 : 400,
                  color: isActive ? '#0ea5e9' : '#64748b',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  transition: 'all 0.15s',
                }}
              >
                <span>{tab.icon}</span>
                {tab.label}
              </button>
            )
          })}
        </div>

        {/* Tab content */}
        <div style={{ padding: 24 }}>
          {activeTab === 'jira' && <JiraSettingsTab />}
          {activeTab === 'openai' && <OpenAISettingsTab />}
        </div>
      </div>
    </div>
  )
}
