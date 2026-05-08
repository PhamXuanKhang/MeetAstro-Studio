import { useState, useEffect, useCallback } from 'react'
import type { PipState } from '../types/electron'

// -webkit-app-region is Electron-specific and not in React.CSSProperties
type DragStyle = React.CSSProperties & { WebkitAppRegion?: 'drag' | 'no-drag' }

const UI = {
  navy: '#0a1530',
  navyMid: '#1a2a52',
  onDark: '#ffffff',
  onDarkMuted: '#a4a097',
  error: '#e03131',
  hairline: '#e5e3df',
  font: "'Notion Sans', Inter, -apple-system, system-ui, 'Segoe UI', Helvetica, sans-serif",
}

function fmtTime(s: number): string {
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

/**
 * Compact always-on-top PIP window rendered when Electron passes --pip-mode.
 * Communicates via IPC: receives pip:state, can trigger stopRecording or focusMain.
 */
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
        background: UI.navy, color: UI.onDark, boxSizing: 'border-box',
        display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
        userSelect: 'none', fontFamily: UI.font,
        WebkitAppRegion: 'drag',
      } as DragStyle}
    >
      {/* Row 1: recording indicator + timer */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{
          width: 10, height: 10, borderRadius: '50%',
          background: state.isRecording ? UI.error : UI.onDarkMuted,
          animation: state.isRecording ? 'blink 1s ease-in-out infinite' : 'none',
          flexShrink: 0,
        }} />
        <span style={{ fontSize: 11, color: UI.onDarkMuted, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1 }}>
          {state.isRecording ? 'Đang ghi âm' : 'Đã dừng'}
        </span>
        <span style={{
          marginLeft: 'auto', fontSize: 22, fontWeight: 700, fontVariantNumeric: 'tabular-nums',
          color: state.isRecording ? UI.error : UI.onDarkMuted, letterSpacing: 2,
        }}>
          {fmtTime(state.elapsedSeconds)}
        </span>
      </div>

      {/* Row 2: last transcript line placeholder */}
      <div style={{ fontSize: 11, color: UI.onDarkMuted, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', minHeight: 16 }}>
        {state.lastTranscriptLine ?? '...'}
      </div>

      {/* Row 3: buttons — non-draggable */}
      <div style={{ display: 'flex', gap: 8, WebkitAppRegion: 'no-drag' } as DragStyle}>
        <button
          onClick={handleRestore}
          style={{
            flex: 1, padding: '6px 0', borderRadius: 8, border: `1px solid ${UI.onDarkMuted}`,
            background: 'transparent', color: UI.onDark, fontWeight: 500, fontSize: 11, cursor: 'pointer', fontFamily: UI.font,
          }}
        >
          ↗ Mở rộng
        </button>
        <button
          onClick={handleStop}
          disabled={stopping}
          style={{
            flex: 1, padding: '6px 0', borderRadius: 8, border: 'none',
            background: stopping ? UI.navyMid : UI.error, color: '#fff',
            fontWeight: 500, fontSize: 11, cursor: stopping ? 'not-allowed' : 'pointer', fontFamily: UI.font,
          }}
        >
          {stopping ? '...' : '⏹ Stop'}
        </button>
      </div>

      <style>{`
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.25} }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { overflow: hidden; }
      `}</style>
    </div>
  )
}
