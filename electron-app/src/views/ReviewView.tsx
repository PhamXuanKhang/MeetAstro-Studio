import { useEffect, useState, useCallback, useMemo, memo } from 'react'
import { useAppStore } from '../store/appStore'
import {
  useActionItemsList,
  useEditActionItem,
  useApproveActionItem,
  useRejectActionItem,
  useBulkApproveActionItems,
} from '../hooks/supabase/useActionItems'
import { pushToJira } from '../api/jira'
import { subscribeActionItemSyncStatus, unsubscribeChannel } from '../api/supabase/realtime'
import ConfidenceBadge from '../components/ConfidenceBadge'
import type { ActionItem, ActionItemPriority } from '../types/supabase-models'
import { buildActionItemTree, ActionItemTreeNode } from '../hooks/supabase/actionitemtree'

interface Props {
  onNavigate: (route: string) => void
  setBusy: (busy: boolean, text?: string) => void
}

// ─── Status Badge (inline, uses Supabase review_status values) ──

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { bg: string; color: string; label: string }> = {
    draft:    { bg: '#f1f5f9', color: '#64748b', label: 'Draft' },
    edited:   { bg: '#fef3c7', color: '#92400e', label: 'Edited' },
    approved: { bg: '#dcfce7', color: '#166534', label: 'Approved' },
    rejected: { bg: '#fee2e2', color: '#991b1b', label: 'Rejected' },
  }
  const s = map[status] ?? map.draft
  return (
    <span style={{ padding: '2px 8px', borderRadius: 4, background: s.bg, color: s.color, fontSize: 10, fontWeight: 700 }}>
      {s.label}
    </span>
  )
}

// ─── Sync Status Badge (Realtime-powered) ───────────────

function SyncBadge({ status, error: syncError }: { status: string; error?: string | null }) {
  const map: Record<string, { bg: string; color: string; label: string }> = {
    pending:  { bg: '#f1f5f9', color: '#64748b', label: '⏳ Pending' },
    syncing:  { bg: '#dbeafe', color: '#1e40af', label: '🔄 Syncing' },
    synced:   { bg: '#dcfce7', color: '#166534', label: '✅ Synced' },
    failed:   { bg: '#fee2e2', color: '#991b1b', label: '❌ Failed' },
  }
  const s = map[status] ?? map.pending
  return (
    <span title={syncError || undefined} style={{ padding: '2px 8px', borderRadius: 4, background: s.bg, color: s.color, fontSize: 10, fontWeight: 600 }}>
      {s.label}
    </span>
  )
}

// ─── ReviewItemCard ─────────────────────────────────────

interface CardProps {
  item: ActionItem
  onToast: (msg: string, err?: boolean) => void
  syncOverride?: { sync_status: string; sync_error: string | null }
}

const ReviewItemCard = memo(function ReviewItemCard({ item, onToast, syncOverride }: CardProps) {
  const meetingId = item.meeting_id

  const { mutate: editItem, isPending: isSaving } = useEditActionItem(meetingId)
  const { mutate: approve, isPending: isApproving } = useApproveActionItem(meetingId)
  const { mutate: reject, isPending: isRejecting } = useRejectActionItem(meetingId)

  const [isEditing, setIsEditing] = useState(false)
  const [editTitle, setEditTitle] = useState(item.title)
  const [editAssignee, setEditAssignee] = useState(item.assignee || '')
  const [editDeadline, setEditDeadline] = useState(item.deadline || '')
  const [editPriority, setEditPriority] = useState<ActionItemPriority>(item.priority)

  const isLowConfidence = item.confidence_score < 0.6 && item.review_status === 'draft'
  const typeLabel = { epic: 'EPIC', task: 'TASK', subtask: 'SUBTASK' }[item.item_type] ?? item.item_type.toUpperCase()

  const syncStatus = syncOverride?.sync_status ?? item.sync_status
  const syncError = syncOverride?.sync_error ?? item.sync_error

  const handleSave = useCallback(() => {
    editItem(
      {
        action_item_id: item.id,
        title: editTitle,
        assignee: editAssignee || null,
        deadline: editDeadline || null,
        priority: editPriority,
      },
      {
        onSuccess: () => { onToast('Đã lưu chỉnh sửa.'); setIsEditing(false) },
        onError: (e) => onToast(`Lỗi lưu: ${e.message}`, true),
      }
    )
  }, [item.id, editTitle, editAssignee, editDeadline, editPriority, editItem, onToast])

  const handleApprove = useCallback(() => {
    approve(item.id, {
      onError: (e) => onToast(`Lỗi approve: ${e.message}`, true),
    })
  }, [item.id, approve, onToast])

  const handleReject = useCallback(() => {
    reject(item.id, {
      onError: (e) => onToast(`Lỗi reject: ${e.message}`, true),
    })
  }, [item.id, reject, onToast])

  const actioning = isApproving || isRejecting

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '7px 10px', border: '1px solid #cbd5e1',
    borderRadius: 6, fontSize: 12, outline: 'none', background: '#fff',
  }

  return (
    <div
      style={{
        padding: 14,
        borderRadius: 12,
        border: `1px solid ${isLowConfidence ? '#fdba74' : '#e2e8f0'}`,
        background: isLowConfidence ? '#fff7ed' : '#fff',
        marginBottom: 10,
      }}
    >
      {/* Top row: type badge, confidence, status, sync, edit button */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8, flexWrap: 'wrap' }}>
        <span style={{ padding: '2px 7px', borderRadius: 4, background: '#dbeafe', color: '#1e40af', fontSize: 10, fontWeight: 700 }}>
          {typeLabel}
        </span>
        <ConfidenceBadge confidence={item.confidence_score} />
        <StatusBadge status={item.review_status} />
        <SyncBadge status={syncStatus} error={syncError} />
        <div style={{ flex: 1 }} />
        {!isEditing && (
          <button
            onClick={() => setIsEditing(true)}
            style={{ padding: '4px 10px', borderRadius: 6, border: '1px solid #cbd5e1', background: '#fff', cursor: 'pointer', fontSize: 12 }}
          >
            ✎ Sửa
          </button>
        )}
      </div>

      {/* Title */}
      <div style={{ fontWeight: 600, fontSize: 13, color: '#0f172a', marginBottom: 6 }}>
        {item.title}
      </div>

      {/* Description */}
      {item.description && (
        <div style={{ fontSize: 12, color: '#475569', marginBottom: 6, lineHeight: 1.5 }}>
          {item.description}
        </div>
      )}

      {/* Meta */}
      <div style={{ fontSize: 11, color: '#64748b', marginBottom: 6 }}>
        👤 {item.assignee || 'TBD'} &nbsp;|&nbsp;
        📅 {item.deadline || 'N/A'} &nbsp;|&nbsp;
        🔥 {item.priority}
      </div>

      {/* Context */}
      {item.context && (
        <div style={{ fontSize: 10, color: '#94a3b8', fontStyle: 'italic', marginBottom: 6 }}>
          💬 {item.context}
        </div>
      )}

      {/* Inline edit form */}
      {isEditing && (
        <div style={{ marginTop: 10, padding: 12, background: '#f8fafc', borderRadius: 8, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <input
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            style={inputStyle}
            placeholder="Title"
          />
          <div style={{ display: 'flex', gap: 8 }}>
            <input value={editAssignee} onChange={(e) => setEditAssignee(e.target.value)} placeholder="Assignee" style={{ ...inputStyle, flex: 1 }} />
            <input value={editDeadline} onChange={(e) => setEditDeadline(e.target.value)} placeholder="YYYY-MM-DD" style={{ ...inputStyle, flex: 1 }} />
            <select value={editPriority} onChange={(e) => setEditPriority(e.target.value as ActionItemPriority)} style={{ ...inputStyle, flex: 1 }}>
              {['critical', 'high', 'medium', 'low'].map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={handleSave}
              disabled={isSaving}
              style={{ padding: '6px 16px', background: '#0ea5e9', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12, fontWeight: 600, opacity: isSaving ? 0.7 : 1 }}
            >
              {isSaving ? 'Đang lưu...' : '💾 Lưu'}
            </button>
            <button
              onClick={() => setIsEditing(false)}
              style={{ padding: '6px 16px', background: '#fff', color: '#64748b', border: '1px solid #e2e8f0', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}
            >
              Hủy
            </button>
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
        <button
          onClick={handleApprove}
          disabled={item.review_status === 'approved' || actioning}
          style={{
            padding: '5px 14px', borderRadius: 6, border: 'none', cursor: 'pointer',
            background: item.review_status === 'approved' ? '#dcfce7' : '#f0fdf4',
            color: '#166534', fontSize: 12, fontWeight: 600,
            opacity: item.review_status === 'approved' || actioning ? 0.6 : 1,
          }}
        >
          ✓ Approve
        </button>
        <button
          onClick={handleReject}
          disabled={item.review_status === 'rejected' || actioning}
          style={{
            padding: '5px 14px', borderRadius: 6, border: 'none', cursor: 'pointer',
            background: item.review_status === 'rejected' ? '#fee2e2' : '#fff1f2',
            color: '#991b1b', fontSize: 12, fontWeight: 600,
            opacity: item.review_status === 'rejected' || actioning ? 0.6 : 1,
          }}
        >
          ✗ Reject
        </button>
      </div>
    </div>
  )
})

// ─── Recursive Tree Renderer ────────────────────────────

function ActionItemTreeRenderer({
  node,
  onToast,
  syncOverrides,
}: {
  node: ActionItemTreeNode
  onToast: (msg: string, err?: boolean) => void
  syncOverrides: Record<string, { sync_status: string; sync_error: string | null }>
}) {
  return (
    <div style={{ marginBottom: node.depth === 0 ? 16 : 8 }}>
      <ReviewItemCard
        item={node.item}
        onToast={onToast}
        syncOverride={syncOverrides[node.item.id]}
      />
      {node.children.length > 0 && (
        <div
          style={{
            marginLeft: 24,
            paddingLeft: 16,
            borderLeft: '2px dashed #cbd5e1',
            marginTop: 8,
          }}
        >
          {node.children.map((child) => (
            <ActionItemTreeRenderer
              key={child.item.id}
              node={child}
              onToast={onToast}
              syncOverrides={syncOverrides}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Toast ──────────────────────────────────────────────

function Toast({ msg, isError, onClose }: { msg: string; isError: boolean; onClose: () => void }) {
  useEffect(() => { const t = setTimeout(onClose, 3500); return () => clearTimeout(t) }, [onClose])
  return (
    <div style={{
      position: 'fixed', bottom: 24, right: 24, zIndex: 999,
      padding: '12px 20px', borderRadius: 10,
      background: isError ? '#fee2e2' : '#dcfce7',
      color: isError ? '#991b1b' : '#166534',
      boxShadow: '0 4px 16px rgba(0,0,0,0.12)', fontSize: 13, fontWeight: 500,
    }}>
      {msg}
    </div>
  )
}

// ─── ReviewView Main ────────────────────────────────────

export default function ReviewView({ onNavigate, setBusy }: Props) {
  const { currentMeetingId, setMeetingStatus } = useAppStore()

  // React Query: action items from Supabase
  const { data: items = [], isLoading } = useActionItemsList(currentMeetingId)
  const { mutate: bulkApprove, isPending: approvingAll } = useBulkApproveActionItems(currentMeetingId)

  const [toast, setToast] = useState<{ msg: string; isError: boolean } | null>(null)
  const [pushing, setPushing] = useState(false)

  // ─── Realtime: sync status overrides ──────────────────
  const [syncOverrides, setSyncOverrides] = useState<Record<string, { sync_status: string; sync_error: string | null }>>({})

  useEffect(() => {
    if (!currentMeetingId) return

    const channel = subscribeActionItemSyncStatus(currentMeetingId, (update) => {
      setSyncOverrides((prev) => ({
        ...prev,
        [update.id]: { sync_status: update.sync_status, sync_error: update.sync_error },
      }))
    })

    return () => { unsubscribeChannel(channel) }
  }, [currentMeetingId])

  const showToast = useCallback((msg: string, isError = false) => {
    setToast({ msg, isError })
  }, [])

  // Compute summary from items
  const summary = useMemo(() => {
    const total = items.length
    const approved = items.filter((i) => i.review_status === 'approved').length
    const rejected = items.filter((i) => i.review_status === 'rejected').length
    const flagged = items.filter((i) => i.confidence_score < 0.6 && i.review_status === 'draft').length
    const pending = items.filter((i) => i.review_status === 'draft' || i.review_status === 'edited').length
    return { total, approved, rejected, flagged, pending }
  }, [items])

  const handleApproveAll = useCallback(() => {
    bulkApprove(undefined, {
      onSuccess: (result) => showToast(`Đã approve ${result.approved_count} items.`),
      onError: (e) => showToast(`Lỗi: ${e.message}`, true),
    })
  }, [bulkApprove, showToast])

  // pushToJira giữ nguyên FastAPI
  const handlePushJira = useCallback(async () => {
    setPushing(true)
    setBusy(true, 'Đang push lên Jira...')
    try {
      await pushToJira(currentMeetingId!)
      setMeetingStatus('pushed')
      showToast('Push lên Jira thành công! 🎉')
    } catch (e) {
      showToast(`Lỗi push Jira: ${e instanceof Error ? e.message : e}`, true)
    } finally {
      setPushing(false)
      setBusy(false)
    }
  }, [currentMeetingId, setBusy, setMeetingStatus, showToast])

  if (!currentMeetingId) {
    return (
      <div style={{ padding: 24, color: '#94a3b8' }}>
        Không có meeting nào được chọn để review.
      </div>
    )
  }

  const pushDisabled = summary.pending > 0 || summary.approved === 0
  const treeNodes = buildActionItemTree(items)

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      {toast && <Toast msg={toast.msg} isError={toast.isError} onClose={() => setToast(null)} />}

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: '#0f172a', marginBottom: 4 }}>
            Review action items
          </h2>
          <p style={{ fontSize: 12, color: '#64748b' }}>
            Approve hoặc reject từng item trước khi push lên Jira.
          </p>
        </div>
        <button
          onClick={() => onNavigate('results')}
          style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid #e2e8f0', background: '#f8fafc', cursor: 'pointer', fontSize: 13 }}
        >
          ← Back
        </button>
      </div>

      {/* Summary bar */}
      <div style={{ background: '#eff6ff', borderRadius: 8, padding: '10px 16px', marginBottom: 12, fontSize: 12, color: '#1e40af' }}>
        Tổng: {summary.total} &nbsp;|&nbsp;
        ✓ Approved: {summary.approved} &nbsp;|&nbsp;
        ⚠ Cần xem: {summary.flagged} &nbsp;|&nbsp;
        ⏳ Chờ: {summary.pending}
      </div>

      {/* Bulk actions */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
        <button
          onClick={handleApproveAll}
          disabled={approvingAll}
          style={{
            padding: '9px 20px', background: '#16a34a', color: '#fff',
            border: 'none', borderRadius: 8, fontWeight: 600, fontSize: 13, cursor: 'pointer',
            opacity: approvingAll ? 0.7 : 1,
          }}
        >
          {approvingAll ? 'Đang approve...' : '✓ Approve all'}
        </button>
        <button
          onClick={handlePushJira}
          disabled={pushDisabled || pushing}
          title={pushDisabled ? 'Approve hoặc reject tất cả items trước khi push' : ''}
          style={{
            padding: '9px 20px', background: '#2563eb', color: '#fff',
            border: 'none', borderRadius: 8, fontWeight: 600, fontSize: 13,
            cursor: pushDisabled || pushing ? 'not-allowed' : 'pointer',
            opacity: pushDisabled || pushing ? 0.5 : 1,
          }}
        >
          {pushing ? 'Đang push...' : '🚀 Push to Jira'}
        </button>
      </div>

      {/* Items list */}
      {isLoading ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#64748b', fontSize: 13 }}>
          <div style={{ width: 18, height: 18, border: '2px solid #0ea5e9', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
          Đang tải...
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      ) : (
        <>
          {treeNodes.length > 0 ? (
            <div>
              {treeNodes.map((node) => (
                <ActionItemTreeRenderer
                  key={node.item.id}
                  node={node}
                  onToast={showToast}
                  syncOverrides={syncOverrides}
                />
              ))}
            </div>
          ) : (
            <div style={{ color: '#94a3b8', fontSize: 13 }}>Không có items để review.</div>
          )}
        </>
      )}
    </div>
  )
}
