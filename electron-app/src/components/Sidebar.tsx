import { useAuthStore } from '../store/authStore'
import { API_BASE_URL } from '../config/api'
import { Button, Icon } from './ui'

const NAV_ITEMS = [
  { route: 'home', label: 'Dashboard', icon: 'dashboard' },
  { route: 'new_meeting', label: 'Cuộc họp mới', icon: 'add_circle' },
  { route: 'history', label: 'Lịch sử', icon: 'history' },
  { route: 'settings', label: 'Cài đặt', icon: 'settings' },
]

interface Props {
  currentRoute: string
  onNavigate: (route: string) => void
}

export default function Sidebar({ currentRoute, onNavigate }: Props) {
  const { user, logout } = useAuthStore()
  const baseUrl = API_BASE_URL

  const initials = user?.name
    ? user.name.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase()
    : user?.email?.[0]?.toUpperCase() ?? '?'

  return (
    <aside
      className="bg-vibrancy"
      style={{
        width: 288,
        minWidth: 288,
        height: '100vh',
        color: 'var(--color-text-main)',
        display: 'flex',
        flexDirection: 'column',
        borderRight: '1px solid var(--color-border-subtle)',
        position: 'relative',
        zIndex: 2,
      }}
    >
      <div style={{ padding: '20px 24px 8px', display: 'flex', gap: 8 }}>
        <span style={{ width: 12, height: 12, borderRadius: 999, background: '#FF5F56' }} />
        <span style={{ width: 12, height: 12, borderRadius: 999, background: '#FFBD2E' }} />
        <span style={{ width: 12, height: 12, borderRadius: 999, background: '#27C93F' }} />
      </div>

      <div style={{ padding: '16px 24px', display: 'flex', alignItems: 'center', gap: 10 }}>
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: 8,
            background: 'linear-gradient(135deg, var(--color-brand-500), var(--color-brand-700))',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            boxShadow: 'var(--shadow-card-hover)',
            flexShrink: 0,
          }}
        >
          <Icon name="hub" size={20} />
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: 18, letterSpacing: '-0.03em' }}>MeetAstro</div>
          <div style={{ fontSize: 11, color: 'var(--color-text-subtle)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 190 }}>{baseUrl}</div>
        </div>
      </div>

      <nav className="custom-scrollbar" style={{ flex: 1, padding: '8px 16px', overflowY: 'auto' }}>
        <div style={{ padding: '8px 8px 10px', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--color-text-subtle)' }}>
          Workspace
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {NAV_ITEMS.map((item) => {
            const isActive = currentRoute === item.route
            return (
              <button
                key={item.route}
                onClick={() => onNavigate(item.route)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  width: '100%',
                  padding: '7px 12px',
                  background: isActive ? 'color-mix(in srgb, var(--color-primary) 10%, transparent)' : 'transparent',
                  border: '1px solid transparent',
                  borderRadius: 8,
                  cursor: 'pointer',
                  color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
                  fontSize: 13,
                  fontWeight: 600,
                  textAlign: 'left',
                  transition: 'background 150ms ease-out, color 150ms ease-out, border-color 150ms ease-out',
                }}
              >
                <Icon name={item.icon} size={18} fill={isActive} />
                <span>{item.label}</span>
              </button>
            )
          })}
        </div>
      </nav>

      <div style={{ borderTop: '1px solid var(--color-border-subtle)', padding: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 8px 12px' }}>
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 999,
              background: 'color-mix(in srgb, var(--color-primary) 12%, var(--color-surface))',
              border: '1px solid color-mix(in srgb, var(--color-primary) 20%, transparent)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 12,
              fontWeight: 800,
              color: 'var(--color-primary)',
              flexShrink: 0,
            }}
          >
            {initials}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            {user?.name && (
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--color-text-main)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {user.name}
              </div>
            )}
            <div style={{ fontSize: 11, color: 'var(--color-text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user?.email}
            </div>
          </div>
        </div>
        <Button variant="ghost" size="sm" onClick={logout} style={{ width: '100%', justifyContent: 'flex-start', color: 'var(--color-text-muted)' }}>
          <Icon name="power_settings_new" size={18} />
          Đăng xuất
        </Button>
      </div>
    </aside>
  )
}
