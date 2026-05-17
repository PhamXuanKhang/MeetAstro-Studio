import { Badge, Icon } from './ui'

interface Props {
  score?: number | null
  confidence?: number | null
}

export default function ConfidenceBadge({ score, confidence }: Props) {
  const value = score ?? confidence
  if (value === null || value === undefined) return null
  const pct = Math.round(value * 100)
  const variant = pct >= 80 ? 'success' : pct < 50 ? 'error' : 'warning'
  const icon = pct >= 80 ? 'check_circle' : pct < 50 ? 'error' : 'warning'
  return <Badge variant={variant} size="sm"><Icon name={icon} size={14} />{pct}%</Badge>
}
