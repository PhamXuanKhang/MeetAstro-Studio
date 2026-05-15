import { Icon } from './ui'

interface Step { n: number; label: string; done?: boolean }
interface Props { current: number }

const STEPS: Step[] = [
  { n: 1, label: 'Upload' },
  { n: 2, label: 'Transcribe' },
  { n: 3, label: 'Analyze' },
]

export default function StepBadge({ current }: Props) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      {STEPS.map((s, i) => {
        const done = s.n < current
        const isCurrent = s.n === current
        return (
          <div key={s.n} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 8px', borderRadius: 4, background: done || isCurrent ? 'color-mix(in srgb, var(--color-primary) 10%, transparent)' : 'var(--color-surface-2)', color: done || isCurrent ? 'var(--color-primary)' : 'var(--color-text-muted)', fontSize: 12, fontWeight: 700 }}>
              {done ? <Icon name="check" size={14} /> : s.n} {s.label}
            </span>
            {i < STEPS.length - 1 && <Icon name="chevron_right" size={16} style={{ color: 'var(--color-text-subtle)' }} />}
          </div>
        )
      })}
    </div>
  )
}
