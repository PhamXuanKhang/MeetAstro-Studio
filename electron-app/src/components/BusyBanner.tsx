interface Props {
  text: string
}

export default function BusyBanner({ text }: Props) {
  return (
    <div
      style={{
        background: '#fef3c7',
        borderBottom: '1px solid #fcd34d',
        padding: '8px 24px',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        fontSize: 13,
        color: '#92400e',
      }}
    >
      <span
        style={{
          display: 'inline-block',
          width: 16,
          height: 16,
          border: '2px solid #f59e0b',
          borderTopColor: 'transparent',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
        }}
      />
      {text || 'Đang xử lý...'}
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
