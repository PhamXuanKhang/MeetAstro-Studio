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
        height: 60,
        background: '#fff',
        borderBottom: '1px solid #e2e8f0',
        display: 'flex',
        alignItems: 'center',
        padding: '0 24px',
        gap: 16,
        flexShrink: 0,
      }}
    >
      <h1 style={{ fontSize: 18, fontWeight: 700, color: '#0f172a', flex: 'none' }}>{title}</h1>
      <div style={{ flex: 1 }} />
      <input
        type="search"
        placeholder="Tìm kiếm cuộc họp..."
        value={searchValue}
        onChange={(e) => onSearchChange(e.target.value)}
        style={{
          width: 220,
          padding: '7px 12px',
          border: '1px solid #cbd5e1',
          borderRadius: 8,
          fontSize: 13,
          outline: 'none',
          background: '#f8fafc',
        }}
      />
      <button
        onClick={onRecordClick}
        style={{
          padding: '8px 16px',
          background: '#ef4444',
          color: '#fff',
          border: 'none',
          borderRadius: 8,
          fontSize: 13,
          fontWeight: 600,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
        }}
      >
        🎙️ Ghi âm
      </button>
    </header>
  )
}
