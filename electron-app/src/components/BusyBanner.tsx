import { Icon } from './ui'

interface Props { text: string }

export default function BusyBanner({ text }: Props) {
  return (
    <div style={{ background: 'color-mix(in srgb, var(--color-warning) 10%, var(--color-surface))', borderBottom: '1px solid color-mix(in srgb, var(--color-warning) 30%, transparent)', padding: '8px 16px', display: 'flex', alignItems: 'center', gap: 10, fontSize: 13, color: 'var(--color-warning)', flexShrink: 0 }}>
      <Icon name="progress_activity" size={18} style={{ animation: 'spin 1s linear infinite' }} />
      <span>{text}</span>
    </div>
  )
}
