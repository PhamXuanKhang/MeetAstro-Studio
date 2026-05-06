import { useCallback } from 'react'

interface Props {
  audioPath: string | null
  onAudioPicked: (path: string) => void
  openFile: (filters?: { name: string; extensions: string[] }[]) => Promise<string | null>
  onToast: (msg: string) => void
}

export default function UploadTab({ audioPath, onAudioPicked, openFile, onToast }: Props) {
  const handlePickFile = useCallback(async () => {
    const path = await openFile([{ name: 'Audio Files', extensions: ['wav', 'mp3', 'm4a', 'ogg', 'flac'] }])
    if (path) {
      onAudioPicked(path)
      onToast('Đã chọn file: ' + path.split(/[\\/]/).pop())
    }
  }, [openFile, onAudioPicked, onToast])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <button
        onClick={handlePickFile}
        style={{
          padding: '32px 20px',
          border: '2px dashed #cbd5e1',
          borderRadius: 12,
          background: '#f8fafc',
          cursor: 'pointer',
          fontSize: 14,
          color: '#64748b',
          fontWeight: 500,
          textAlign: 'center',
          transition: 'border-color 0.15s, background 0.15s',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = '#0ea5e9'
          e.currentTarget.style.background = '#f0f9ff'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = '#cbd5e1'
          e.currentTarget.style.background = '#f8fafc'
        }}
      >
        📂 Nhấp để chọn file audio
        <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 6 }}>
          WAV, MP3, M4A, OGG, FLAC
        </div>
      </button>

      {audioPath && (
        <div style={{ fontSize: 12, color: '#16a34a', padding: '8px 12px', background: '#f0fdf4', borderRadius: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
          <span>✓</span>
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {audioPath.split(/[\\/]/).pop()}
          </span>
        </div>
      )}
    </div>
  )
}
