import type { ReviewStatus } from '../types/schema'

interface Props {
  status: ReviewStatus
}

const STATUS_MAP: Record<ReviewStatus, { label: string; bg: string; color: string }> = {
  approved: { label: '✓ Approved', bg: '#dcfce7', color: '#166534' },
  rejected: { label: '✗ Rejected', bg: '#fee2e2', color: '#991b1b' },
  edited:   { label: '✎ Edited',   bg: '#dbeafe', color: '#1e40af' },
  draft:    { label: '⏳ Draft',    bg: '#f1f5f9', color: '#475569' },
}

export default function StatusBadge({ status }: Props) {
  const s = STATUS_MAP[status] ?? STATUS_MAP.draft
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: 12,
        background: s.bg,
        color: s.color,
        fontSize: 11,
        fontWeight: 600,
      }}
    >
      {s.label}
    </span>
  )
}
