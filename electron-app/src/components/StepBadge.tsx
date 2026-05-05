interface Props {
  step: 1 | 2 | 3
  audioReady: boolean
  transcriptReady: boolean
  analysisReady: boolean
}

/**
 * 3-step pipeline indicator.
 * Mirrors _step_badge() trong frontend/views/new_meeting_view.py.
 */
export default function StepBadge({ step, audioReady, transcriptReady, analysisReady }: Props) {
  const steps = [
    { n: 1, label: 'Audio', done: audioReady },
    { n: 2, label: 'Transcript', done: transcriptReady },
    { n: 3, label: 'Phân tích', done: analysisReady },
  ]

  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 20 }}>
      {steps.map((s, i) => {
        const isCurrent = s.n === step
        const bg = s.done ? '#22c55e' : isCurrent ? '#0ea5e9' : '#e2e8f0'
        const color = s.done || isCurrent ? '#fff' : '#94a3b8'
        return (
          <div key={s.n} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '5px 12px',
                borderRadius: 20,
                background: bg,
                color,
                fontSize: 12,
                fontWeight: 600,
              }}
            >
              {s.done ? '✓' : s.n} {s.label}
            </div>
            {i < 2 && <span style={{ color: '#cbd5e1', fontSize: 16 }}>→</span>}
          </div>
        )
      })}
    </div>
  )
}
