import { useCallback } from 'react'
import { Icon } from '../ui'

const AUDIO_EXTS = ['wav', 'mp3', 'm4a', 'ogg']
const VIDEO_EXTS = ['mp4', 'mkv', 'webm']
const ALL_EXTS = [...AUDIO_EXTS, ...VIDEO_EXTS]

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
          border: '1px dashed var(--color-border)',
          borderRadius: 14,
          background: 'var(--color-surface-2)',
          cursor: 'pointer',
          fontSize: 14,
          color: 'var(--color-text-muted)',
          fontWeight: 600,
          textAlign: 'center',
          transition: 'border-color 0.15s, background 0.15s',
        }}
      >
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}><Icon name="perm_media" size={20} /> Nhấp để chọn file</span>
        <div style={{ fontSize: 12, color: 'var(--color-text-subtle)', marginTop: 6 }}>
          Audio: WAV, MP3, M4A, OGG &nbsp;|&nbsp; Video: MP4, MKV, WEBM
        </div>
      </button>

      {audioPath && (
        <div style={{ fontSize: 13, color: 'var(--color-success)', padding: '8px 12px', background: 'color-mix(in srgb, var(--color-success) 10%, transparent)', borderRadius: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Icon name="check_circle" size={18} />
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {audioPath.split(/[\\/]/).pop()}
          </span>
        </div>
      )}
    </div>
  )
}
