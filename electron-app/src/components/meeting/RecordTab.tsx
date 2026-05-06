import { useCallback } from 'react'

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
          <button
            onClick={handleStart}
            style={{
              padding: '10px 22px',
              background: '#ef4444',
              color: '#fff',
              border: 'none',
              borderRadius: 8,
              fontWeight: 700,
              fontSize: 14,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
            }}
          >
            ⏺ Bắt đầu ghi
          </button>
        ) : (
          <>
            <button
              onClick={handleStop}
              style={{
                padding: '10px 22px',
                background: '#1e293b',
                color: '#fff',
                border: 'none',
                borderRadius: 8,
                fontWeight: 700,
                fontSize: 14,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              ⏹ Dừng ghi
            </button>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  background: '#ef4444',
                  animation: 'blink 1s ease-in-out infinite',
                  display: 'inline-block',
                }}
              />
              <span style={{ fontSize: 14, fontWeight: 700, color: '#ef4444', fontVariantNumeric: 'tabular-nums' }}>
                {fmtTime(elapsedSeconds)}
              </span>
              <span style={{ fontSize: 12, color: '#ef4444' }}>ĐANG GHI</span>
            </div>
            <style>{`@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.2} }`}</style>
          </>
        )}
      </div>

      {audioPath && !isRecording && (
        <div style={{ fontSize: 12, color: '#16a34a', padding: '8px 12px', background: '#f0fdf4', borderRadius: 8, display: 'flex', alignItems: 'center', gap: 8 }}>
          <span>✓ Đã ghi:</span>
          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {audioPath.split(/[\\/]/).pop()}
          </span>
        </div>
      )}

      <div style={{ fontSize: 12, color: '#94a3b8' }}>
        Ghi âm trực tiếp từ microphone. File WAV 16kHz mono.
      </div>
    </div>
  )
}
