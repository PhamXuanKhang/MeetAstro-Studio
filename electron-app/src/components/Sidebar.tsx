import { useAuthStore } from '../store/authStore'

const NAV_ITEMS = [
  { route: 'home', label: 'Dashboard', icon: '🏠' },
  { route: 'new_meeting', label: 'Cuộc họp mới', icon: '➕' },
  { route: 'history', label: 'Lịch sử', icon: '📋' },
  { route: 'settings', label: 'Cài đặt', icon: '⚙️' },
]

interface Props {
  currentRoute: string
  onNavigate: (route: string) => void
}

export default function Sidebar({ currentRoute, onNavigate }: Props) {
  const { user, logout } = useAuthStore()
  const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

  const initials = user?.name
    ? user.name.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase()
    : user?.email?.[0]?.toUpperCase() ?? '?'

  return (
    <aside
      style={{
        width: 260,
        minWidth: 260,
        background: '#1e293b',
        color: '#f1f5f9',
        display: 'flex',
        flexDirection: 'column',
        padding: '16px 0',
        borderRight: '1px solid #334155',
      }}
    >
      {/* App identity */}
      <div style={{ padding: '0 20px 24px' }}>
        <div
          style={{
            width: 40,
            height: 40,
            background: '#0ea5e9',
            borderRadius: 10,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 20,
            marginBottom: 12,
          }}
        >
          🎙️
        </div>
        <div style={{ fontWeight: 700, fontSize: 15, color: '#f1f5f9' }}>AI Meeting Assistant</div>
        <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>{baseUrl}</div>
      </div>

      {/* Nav items */}
      <nav style={{ flex: 1 }}>
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
                padding: '10px 20px',
                background: isActive ? '#0f172a' : 'transparent',
                border: 'none',
                cursor: 'pointer',
                color: isActive ? '#38bdf8' : '#94a3b8',
                fontSize: 14,
                fontWeight: isActive ? 600 : 400,
                textAlign: 'left',
                borderLeft: isActive ? '3px solid #38bdf8' : '3px solid transparent',
                transition: 'all 0.15s',
              }}
            >
              <span style={{ fontSize: 16 }}>{item.icon}</span>
              {item.label}
            </button>
          )
        })}
      </nav>

      {/* User info + logout */}
      <div style={{ borderTop: '1px solid #334155', padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 10 }}>
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: '50%',
            background: '#0ea5e9',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 13,
            fontWeight: 700,
            color: '#fff',
            flexShrink: 0,
          }}
        >
          {initials}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          {user?.name && (
            <div style={{ fontSize: 12, fontWeight: 600, color: '#f1f5f9', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user.name}
            </div>
          )}
          <div style={{ fontSize: 11, color: '#64748b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {user?.email}
          </div>
        </div>
        <button
          onClick={logout}
          title="Đăng xuất"
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: '#64748b',
            fontSize: 16,
            padding: 4,
            flexShrink: 0,
          }}
        >
          ↩
        </button>
      </div>

      <div style={{ padding: '8px 20px', fontSize: 11, color: '#334155' }}>
        v0.1.0 • AI Meeting Assistant
      </div>
    </aside>
  )
}
