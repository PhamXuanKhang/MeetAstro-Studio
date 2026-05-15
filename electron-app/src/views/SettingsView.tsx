import { useState } from 'react'
import JiraSettingsTab from '../components/settings/JiraSettingsTab'
import OpenAISettingsTab from '../components/settings/OpenAISettingsTab'
import { Card, Icon } from '../components/ui'

type Tab = 'jira' | 'openai'

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'jira', label: 'Jira', icon: 'lan' },
  { id: 'openai', label: 'OpenAI', icon: 'smart_toy' },
]

export default function SettingsView() {
  const [activeTab, setActiveTab] = useState<Tab>('jira')

  return (
    <div style={{ maxWidth: 760, margin: '0 auto' }}>
      <Card style={{ overflow: 'hidden' }}>
        <div style={{ display: 'flex', borderBottom: '1px solid var(--color-border-subtle)', background: 'var(--color-surface)' }}>
          {TABS.map((tab) => {
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  flex: 1,
                  padding: '14px 20px',
                  background: isActive ? 'var(--color-surface)' : 'var(--color-surface-2)',
                  border: 'none',
                  borderBottom: isActive ? '2px solid var(--color-primary)' : '2px solid transparent',
                  cursor: 'pointer',
                  fontSize: 14,
                  fontWeight: 700,
                  color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  transition: 'background 0.15s, color 0.15s, border-color 0.15s',
                }}
              >
                <Icon name={tab.icon} size={18} fill={isActive} />
                {tab.label}
              </button>
            )
          })}
        </div>
        <div style={{ padding: 24 }}>
          {activeTab === 'jira' && <JiraSettingsTab />}
          {activeTab === 'openai' && <OpenAISettingsTab />}
        </div>
      </Card>
    </div>
  )
}
