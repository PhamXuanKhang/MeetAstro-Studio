import { useCallback } from 'react'

const AUDIO_EXTS = ['wav', 'mp3', 'm4a', 'ogg', 'flac']
const VIDEO_EXTS = ['mp4', 'mkv', 'webm']
const ALL_EXTS = [...AUDIO_EXTS, ...VIDEO_EXTS]

const UI = {
  ink: '#1a1a1a',
  slate: '#5d5b54',
  steel: '#787671',
  hairline: '#e5e3df',
  hairlineStrong: '#c8c4be',
  surface: '#f6f5f4',
  mint: '#d9f3e1',
  success: '#1aae39',
  font: "'Notion Sans', Inter, -apple-system, system-ui, 'Segoe UI', Helvetica, sans-serif",
}

interface Props {
  audioPath: string | null
  onAudioPicked: (path: string) => void
  openFile: (filters?: { name: string; extensions: string[] }[]) => Promise<string | null>
  onToast: (msg: string) => void
}

export default function UploadTab({ audioPath, onAudioPicked, openFile, onToast }: Props) {
  const handlePickFile = useCallback(async () => {
    const path = await openFile([
      { name: 'Audio / Video Files', extensions: ALL_EXTS },
      { name: 'Audio Files', extensions: AUDIO_EXTS },
      { name: 'Video Files', extensions: VIDEO_EXTS },
    ])
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
          border: `1px dashed ${UI.hairlineStrong}`,
          borderRadius: 12,
          background: UI.surface,
          cursor: 'pointer',
          fontSize: 14,
          color: UI.slate,
          fontWeight: 500,
          textAlign: 'center',
          transition: 'border-color 0.15s, background 0.15s',
          fontFamily: UI.font,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = UI.ink
          e.currentTarget.style.background = '#fafaf9'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = UI.hairlineStrong
          e.currentTarget.style.background = UI.surface
        }}
      >
        📂 Nhấp để chọn file
        <div style={{ fontSize: 12, color: UI.steel, marginTop: 6 }}>
          Audio: WAV, MP3, M4A, OGG, FLAC &nbsp;|&nbsp; Video: MP4, MKV, WEBM
        </div>
      </button>

      {audioPath && (
        <div style={{ fontSize: 13, color: UI.success, padding: '8px 12px', background: UI.mint, borderRadius: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
          <span>✓</span>
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {audioPath.split(/[\\/]/).pop()}
          </span>
        </div>
      )}
    </div>
  )
}
