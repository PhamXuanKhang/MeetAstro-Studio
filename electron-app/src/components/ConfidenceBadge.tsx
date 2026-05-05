interface Props {
  confidence: number
  size?: 'sm' | 'md'
}

/**
 * Confidence badge với màu theo ngưỡng.
 * Mirrors _confidence_badge() trong frontend/views/results_view.py và review_view.py.
 * Thresholds: < 0.4 = red, < 0.7 = orange, >= 0.7 = green
 */
export default function ConfidenceBadge({ confidence, size = 'sm' }: Props) {
  const pct = Math.round(confidence * 100)
  let bg = '#dcfce7'
  let color = '#166534'
  let symbol = '✓'

  if (confidence < 0.4) {
    bg = '#fee2e2'
    color = '#991b1b'
    symbol = '⚠'
  } else if (confidence < 0.7) {
    bg = '#fef3c7'
    color = '#92400e'
    symbol = '~'
  }

  const fontSize = size === 'sm' ? 11 : 12

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 3,
        padding: '2px 7px',
        borderRadius: 12,
        background: bg,
        color,
        fontSize,
        fontWeight: 600,
      }}
    >
      {symbol} {pct}%
    </span>
  )
}
