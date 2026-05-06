import type { ReactNode } from 'react'

interface Props {
  children: ReactNode
}

export default function AuthLayout({ children }: Props) {
  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#f1f5f9',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
    >
      <div style={{ width: '100%', maxWidth: 400 }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div
            style={{
              width: 52,
              height: 52,
              background: '#0ea5e9',
              borderRadius: 14,
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 26,
              marginBottom: 12,
            }}
          >
            🎙️
          </div>
          <div style={{ fontWeight: 800, fontSize: 20, color: '#0f172a' }}>AI Meeting Assistant</div>
          <div style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>
            Chuyển đổi cuộc họp thành action items
          </div>
        </div>
        <div
          style={{
            background: '#fff',
            borderRadius: 16,
            border: '1px solid #e2e8f0',
            padding: '32px 28px',
            boxShadow: '0 4px 24px rgba(0,0,0,0.06)',
          }}
        >
          {children}
        </div>
      </div>
    </div>
  )
}
