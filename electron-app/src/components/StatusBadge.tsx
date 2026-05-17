import { Badge } from './ui'

type Status = 'approved' | 'rejected' | 'edited' | 'draft' | string

export default function StatusBadge({ status }: { status: Status }) {
  const map: Record<string, { label: string; variant: 'default' | 'primary' | 'success' | 'warning' | 'error' | 'info' }> = {
    approved: { label: 'Approved', variant: 'success' },
    rejected: { label: 'Rejected', variant: 'error' },
    edited: { label: 'Edited', variant: 'info' },
    draft: { label: 'Draft', variant: 'default' },
  }
  const item = map[status] ?? { label: status, variant: 'default' as const }
  return <Badge variant={item.variant} size="sm" dot>{item.label}</Badge>
}
