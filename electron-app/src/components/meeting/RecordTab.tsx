import { useCallback } from 'react'
import { Button, Icon } from '../ui'

function fmtTime(s: number): string {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

interface Props {
  isRecording: boolean
  elapsedSeconds: number
  audioPath: string | null
  onStart: () => void
  onStop: () => void
}

export default function RecordTab({ isRecording, elapsedSeconds, audioPath, onStart, onStop }: Props) {
  const handleStart = useCallback(() => onStart(), [onStart])
  const handleStop = useCallback(() => onStop(), [onStop])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        {!isRecording ? (
          <Button onClick={handleStart} variant="danger">
            <Icon name="radio_button_checked" size={18} />
            Bắt đầu ghi
          </Button>
        ) : (
          <>
            <Button onClick={handleStop} variant="secondary">
              <Icon name="stop_circle" size={18} />
              Dừng ghi
            </Button>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: 'var(--color-danger)', animation: 'blink 1s ease-in-out infinite', display: 'inline-block' }} />
              <span style={{ fontSize: 14, fontWeight: 800, color: 'var(--color-danger)', fontVariantNumeric: 'tabular-nums' }}>{fmtTime(elapsedSeconds)}</span>
              <span style={{ fontSize: 12, color: 'var(--color-danger)', fontWeight: 700 }}>ĐANG GHI</span>
            </div>
            <style>{`@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.2} }`}</style>
          </>
        )}
      </div>

      {audioPath && !isRecording && (
        <div style={{ fontSize: 12, color: 'var(--color-success)', padding: '8px 12px', background: 'color-mix(in srgb, var(--color-success) 10%, transparent)', borderRadius: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Icon name="check_circle" size={16} />
          <span>Đã ghi:</span>
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{audioPath.split(/[\\/]/).pop()}</span>
        </div>
      )}

      <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>Ghi âm trực tiếp từ microphone. File WAV 16kHz mono.</div>
    </div>
  )
}
