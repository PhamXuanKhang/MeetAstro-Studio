import { useState, useEffect, useCallback } from 'react'
import type { PipState } from '../types/electron'
import { Icon } from '../components/ui'

type DragStyle = React.CSSProperties & { WebkitAppRegion?: 'drag' | 'no-drag' }

function fmtTime(s: number): string {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

export default function MiniPopupView() {
  const [state, setState] = useState<PipState>({ isRecording: true, elapsedSeconds: 0 })
  const [stopping, setStopping] = useState(false)

  useEffect(() => {
    const cleanup = window.electronAPI?.onPipStateUpdate?.((s) => setState(s))
    return () => cleanup?.()
  }, [])

  const handleStop = useCallback(async () => {
    if (stopping) return
    setStopping(true)
    await window.electronAPI?.pipStopRecording?.()
  }, [stopping])

  const handleRestore = useCallback(async () => {
    await window.electronAPI?.pipFocusMain?.()
  }, [])

  return (
    <div
      style={{
        width: '100vw', height: '100vh', margin: 0, padding: '14px 16px',
        background: 'var(--color-bg)', color: 'var(--color-text-main)', boxSizing: 'border-box',
        display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
        userSelect: 'none', WebkitAppRegion: 'drag', border: '1px solid var(--color-border-subtle)',
      } as DragStyle}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ width: 10, height: 10, borderRadius: '50%', background: state.isRecording ? 'var(--color-danger)' : 'var(--color-text-subtle)', animation: state.isRecording ? 'blink 1s ease-in-out infinite' : 'none', flexShrink: 0 }} />
        <span style={{ fontSize: 11, color: 'var(--color-text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1 }}>
          {state.isRecording ? 'Đang ghi âm' : 'Đã dừng'}
        </span>
        <span style={{ marginLeft: 'auto', fontSize: 22, fontWeight: 800, fontVariantNumeric: 'tabular-nums', color: state.isRecording ? 'var(--color-danger)' : 'var(--color-text-muted)', letterSpacing: 2 }}>
          {fmtTime(state.elapsedSeconds)}
        </span>
      </div>
      <div style={{ fontSize: 11, color: 'var(--color-text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', minHeight: 16 }}>
        {state.lastTranscriptLine ?? '...'}
      </div>
      <div style={{ display: 'flex', gap: 8, WebkitAppRegion: 'no-drag' } as DragStyle}>
        <button onClick={handleRestore} style={{ flex: 1, padding: '6px 0', borderRadius: 8, border: '1px solid var(--color-border)', background: 'var(--color-surface)', color: 'var(--color-text-main)', fontWeight: 700, fontSize: 11, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
          <Icon name="open_in_full" size={14} /> Mở rộng
        </button>
        <button onClick={handleStop} disabled={stopping} style={{ flex: 1, padding: '6px 0', borderRadius: 8, border: 'none', background: stopping ? 'var(--color-surface-3)' : 'var(--color-danger)', color: 'white', fontWeight: 700, fontSize: 11, cursor: stopping ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4 }}>
          <Icon name={stopping ? 'progress_activity' : 'stop_circle'} size={14} style={stopping ? { animation: 'spin 1s linear infinite' } : undefined} />
          {stopping ? '...' : 'Stop'}
        </button>
      </div>
      <style>{`@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.25} } body { overflow: hidden; }`}</style>
    </div>
  )
}
