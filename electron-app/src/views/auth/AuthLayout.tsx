import type { ReactNode } from 'react'
import { Card, Icon } from '../../components/ui'

interface Props {
  children: ReactNode
}

export default function AuthLayout({ children }: Props) {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--color-bg)',
        padding: 16,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div className="landing-grid" style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }} />
      <div style={{ position: 'relative', zIndex: 1, width: '100%', maxWidth: 448 }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div
            style={{
              width: 52,
              height: 52,
              background: 'linear-gradient(135deg, var(--color-brand-500), var(--color-brand-700))',
              borderRadius: 8,
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              marginBottom: 12,
              boxShadow: 'var(--shadow-card-hover)',
            }}
          >
            <Icon name="hub" size={26} />
          </div>
          <div style={{ fontWeight: 800, fontSize: 30, letterSpacing: '-0.04em', color: 'var(--color-primary)' }}>MeetAstro</div>
          <div style={{ fontSize: 14, color: 'var(--color-text-muted)', marginTop: 6 }}>
            Chuyển đổi cuộc họp thành action items
          </div>
        </div>
        <Card style={{ padding: '32px 28px', boxShadow: 'var(--shadow-elev)' }}>
          {children}
        </Card>
      </div>
    </div>
  )
}
