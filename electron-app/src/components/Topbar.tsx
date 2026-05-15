import { Button, Icon } from './ui'

interface Props {
  title: string
  searchValue: string
  onSearchChange: (q: string) => void
  onRecordClick: () => void
}

export default function Topbar({ title, searchValue, onSearchChange, onRecordClick }: Props) {
  return (
    <header
      style={{
        minHeight: 56,
        borderBottom: '1px solid var(--color-border-subtle)',
        display: 'flex',
        alignItems: 'center',
        padding: '12px 32px 8px',
        gap: 16,
        flexShrink: 0,
        background: 'transparent',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
        <Icon name="chevron_right" size={18} style={{ color: 'var(--color-text-subtle)' }} />
        <h1 style={{ fontSize: 24, fontWeight: 700, letterSpacing: '-0.03em', color: 'var(--color-text-main)', margin: 0, whiteSpace: 'nowrap' }}>{title}</h1>
      </div>
      <div style={{ flex: 1 }} />
      <label
        style={{
          width: 260,
          height: 36,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '0 12px',
          borderRadius: 8,
          border: '1px solid var(--color-border)',
          background: 'color-mix(in srgb, var(--color-surface) 72%, transparent)',
          color: 'var(--color-text-muted)',
        }}
      >
        <Icon name="search" size={18} />
        <input
          type="search"
          placeholder="Tìm kiếm cuộc họp..."
          value={searchValue}
          onChange={(e) => onSearchChange(e.target.value)}
          style={{
            width: '100%',
            border: 0,
            outline: 'none',
            background: 'transparent',
            color: 'var(--color-text-main)',
            fontSize: 13,
            minWidth: 0,
          }}
        />
      </label>
      <Button variant="primary" size="md" onClick={onRecordClick}>
        <Icon name="mic" size={18} />
        Ghi âm
      </Button>
    </header>
  )
}
