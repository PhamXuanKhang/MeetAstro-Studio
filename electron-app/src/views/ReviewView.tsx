import { useEffect, useState, useCallback, memo } from 'react'
import { useAppStore } from '../store/appStore'
import { listReviewItems, getReviewSummary, patchReviewItem, approveItem, rejectItem, approveAll } from '../api/review'
import { pushToJira } from '../api/jira'
import ConfidenceBadge from '../components/ConfidenceBadge'
import StatusBadge from '../components/StatusBadge'
import type { ReviewItemResponse, ReviewSummaryResponse, Priority } from '../types/schema'

interface Props {
  onNavigate: (route: string) => void
  setBusy: (busy: boolean, text?: string) => void
}

// --- ReviewItemCard ---
interface CardProps {
  item: ReviewItemResponse
  meetingId: string
  onReload: () => void
  onToast: (msg: string, err?: boolean) => void
}

const ReviewItemCard = memo(function ReviewItemCard({ item, meetingId, onReload, onToast }: CardProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editSummary, setEditSummary] = useState(item.edited_summary || item.summary)
  const [editAssignee, setEditAssignee] = useState(item.edited_assignee || item.assignee || '')
  const [editDeadline, setEditDeadline] = useState(item.edited_deadline || item.deadline || '')
  const [editPriority, setEditPriority] = useState<Priority>((item.edited_priority as Priority) || item.priority || 'Medium')
  const [saving, setSaving] = useState(false)
  const [actioning, setActioning] = useState(false)

  const isHighlighted = item.is_flagged && item.review_status === 'draft'
  const effectiveSummary = item.edited_summary || item.summary
  const effectiveAssignee = item.edited_assignee || item.assignee
  const effectiveDeadline = item.edited_deadline || item.deadline
  const typeLabel = { epic: 'EPIC', task: 'TASK', subtask: 'SUBTASK' }[item.item_type] ?? item.item_type.toUpperCase()

  const handleSave = useCallback(async () => {
    setSaving(true)
    try {
      await patchReviewItem(meetingId, item.id!, {
        edited_summary: editSummary || null,
        edited_assignee: editAssignee || null,
        edited_deadline: editDeadline || null,
        edited_priority: editPriority || null,
      })
      onToast('Đã lưu chỉnh sửa.')
      setIsEditing(false)
      onReload()
    } catch (e) {
      onToast(`Lỗi lưu: ${e instanceof Error ? e.message : e}`, true)
    } finally {
      setSaving(false)
    }
  }, [meetingId, item.id, editSummary, editAssignee, editDeadline, editPriority, onToast, onReload])

  const handleApprove = useCallback(async () => {
    setActioning(true)
    try {
      await approveItem(meetingId, item.id!)
      onReload()
    } catch (e) {
      onToast(`Lỗi approve: ${e instanceof Error ? e.message : e}`, true)
    } finally {
      setActioning(false)
    }
  }, [meetingId, item.id, onToast, onReload])

  const handleReject = useCallback(async () => {
    setActioning(true)
    try {
      await rejectItem(meetingId, item.id!)
      onReload()
    } catch (e) {
      onToast(`Lỗi reject: ${e instanceof Error ? e.message : e}`, true)
    } finally {
      setActioning(false)
    }
  }, [meetingId, item.id, onToast, onReload])

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '7px 10px', border: '1px solid #cbd5e1',
    borderRadius: 6, fontSize: 12, outline: 'none', background: '#fff',
  }

  return (
    <div
      style={{
        padding: 14,
        borderRadius: 12,
        border: `1px solid ${isHighlighted ? '#fdba74' : '#e2e8f0'}`,
        background: isHighlighted ? '#fff7ed' : '#fff',
        marginBottom: 10,
      }}
    >
      {/* Top row: type badge, index, confidence, status, edit button */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8, flexWrap: 'wrap' }}>
        <span style={{ padding: '2px 7px', borderRadius: 4, background: '#dbeafe', color: '#1e40af', fontSize: 10, fontWeight: 700 }}>
          {typeLabel}
        </span>
        <span style={{ fontSize: 10, color: '#94a3b8' }}>[{item.item_index}]</span>
        <ConfidenceBadge confidence={item.confidence} />
        <StatusBadge status={item.review_status} />
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

      {/* Summary */}
      <div style={{ fontWeight: 600, fontSize: 13, color: '#0f172a', marginBottom: 6 }}>
        {effectiveSummary}
      </div>

      {/* Meta */}
      <div style={{ fontSize: 11, color: '#64748b', marginBottom: 6 }}>
        👤 {effectiveAssignee || 'TBD'} &nbsp;|&nbsp;
        📅 {effectiveDeadline || 'N/A'} &nbsp;|&nbsp;
        🔥 {item.edited_priority || item.priority}
      </div>

      {/* Validation notes */}
      {item.validation_notes.length > 0 && (
        <div style={{ fontSize: 10, color: '#c2410c', marginBottom: 6 }}>
          ⚠ {(item.validation_notes as string[]).join(' | ')}
        </div>
      )}

      {/* Inline edit form */}
      {isEditing && (
        <div style={{ marginTop: 10, padding: 12, background: '#f8fafc', borderRadius: 8, display: 'flex', flexDirection: 'column', gap: 8 }}>
          <textarea
            value={editSummary}
            onChange={(e) => setEditSummary(e.target.value)}
            rows={2}
            style={{ ...inputStyle, resize: 'vertical' }}
            placeholder="Summary"
          />
          <div style={{ display: 'flex', gap: 8 }}>
            <input value={editAssignee} onChange={(e) => setEditAssignee(e.target.value)} placeholder="Assignee" style={{ ...inputStyle, flex: 1 }} />
            <input value={editDeadline} onChange={(e) => setEditDeadline(e.target.value)} placeholder="YYYY-MM-DD" style={{ ...inputStyle, flex: 1 }} />
            <select value={editPriority} onChange={(e) => setEditPriority(e.target.value as Priority)} style={{ ...inputStyle, flex: 1 }}>
              {['Critical', 'High', 'Medium', 'Low'].map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={handleSave}
              disabled={saving}
              style={{ padding: '6px 16px', background: '#0ea5e9', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12, fontWeight: 600, opacity: saving ? 0.7 : 1 }}
            >
              {saving ? 'Đang lưu...' : '💾 Lưu'}
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

// --- Toast ---
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

// --- ReviewView main ---
export default function ReviewView({ onNavigate, setBusy }: Props) {
  const { currentMeetingId, setMeetingStatus } = useAppStore()
  const [items, setItems] = useState<ReviewItemResponse[]>([])
  const [summary, setSummary] = useState<ReviewSummaryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState<{ msg: string; isError: boolean } | null>(null)
  const [pushing, setPushing] = useState(false)
  const [approvingAll, setApprovingAll] = useState(false)

  const showToast = useCallback((msg: string, isError = false) => {
    setToast({ msg, isError })
  }, [])

  const reloadItems = useCallback(async () => {
    if (!currentMeetingId) return
    try {
      const [itemsData, summaryData] = await Promise.all([
        listReviewItems(currentMeetingId),
        getReviewSummary(currentMeetingId),
      ])
      // Map API response to ReviewItem format
      setItems(itemsData)
      setSummary(summaryData)
    } catch (e) {
      showToast(`Lỗi tải review items: ${e instanceof Error ? e.message : e}`, true)
    }
  }, [currentMeetingId, showToast])

  useEffect(() => {
    setLoading(true)
    reloadItems().finally(() => setLoading(false))
  }, [reloadItems])

  const handleApproveAll = useCallback(async () => {
    setApprovingAll(true)
    try {
      const result = await approveAll(currentMeetingId!)
      showToast(`Đã approve ${result.approved_count} items.`)
      await reloadItems()
    } catch (e) {
      showToast(`Lỗi: ${e instanceof Error ? e.message : e}`, true)
    } finally {
      setApprovingAll(false)
    }
  }, [currentMeetingId, showToast, reloadItems])

  const handlePushJira = useCallback(async () => {
    setPushing(true)
    setBusy(true, 'Đang push lên Jira...')
    try {
      await pushToJira(currentMeetingId!)
      setMeetingStatus('pushed')
      showToast('Push lên Jira thành công! 🎉')
      await reloadItems()
    } catch (e) {
      showToast(`Lỗi push Jira: ${e instanceof Error ? e.message : e}`, true)
    } finally {
      setPushing(false)
      setBusy(false)
    }
  }, [currentMeetingId, setBusy, setMeetingStatus, showToast, reloadItems])

  if (!currentMeetingId) {
    return (
      <div style={{ padding: 24, color: '#94a3b8' }}>
        Không có meeting nào được chọn để review.
      </div>
    )
  }

  const pushDisabled = !summary || summary.pending > 0 || summary.approved === 0
  const flagged = items.filter((i) => i.is_flagged && i.review_status === 'draft')
  const normal = items.filter((i) => !(i.is_flagged && i.review_status === 'draft'))

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
      {summary && (
        <div style={{ background: '#eff6ff', borderRadius: 8, padding: '10px 16px', marginBottom: 12, fontSize: 12, color: '#1e40af' }}>
          Tổng: {summary.total} &nbsp;|&nbsp;
          ✓ Approved: {summary.approved} &nbsp;|&nbsp;
          ⚠ Cần xem: {summary.flagged} &nbsp;|&nbsp;
          ⏳ Chờ: {summary.pending}
        </div>
      )}

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
      {loading ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#64748b', fontSize: 13 }}>
          <div style={{ width: 18, height: 18, border: '2px solid #0ea5e9', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
          Đang tải...
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      ) : (
        <>
          {flagged.length > 0 && (
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#c2410c', marginBottom: 8 }}>
                ⚠️ Cần xem ({flagged.length} items — độ tin cậy thấp)
              </div>
              {flagged.map((item) => (
                <ReviewItemCard
                  key={item.id}
                  item={item}
                  meetingId={currentMeetingId}
                  onReload={reloadItems}
                  onToast={showToast}
                />
              ))}
            </div>
          )}
          {normal.length > 0 && (
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#64748b', marginBottom: 8 }}>
                Các items khác ({normal.length})
              </div>
              {normal.map((item) => (
                <ReviewItemCard
                  key={item.id}
                  item={item}
                  meetingId={currentMeetingId}
                  onReload={reloadItems}
                  onToast={showToast}
                />
              ))}
            </div>
          )}
          {items.length === 0 && (
            <div style={{ color: '#94a3b8', fontSize: 13 }}>Không có items để review.</div>
          )}
        </>
      )}
    </div>
  )
}
