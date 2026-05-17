import { useEffect, useState, useCallback, useMemo, memo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAppStore } from '../store/appStore'
import {
  useActionItemsList,
  useEditActionItem,
  useApproveActionItem,
  useRejectActionItem,
  useBulkApproveActionItems,
  useAddManualActionItem,
  useApplyWorkStatusUpdate,
} from '../hooks/supabase/useActionItems'
import { pushToJira } from '../api/jira'
import { getAnalysisResult } from '../api/supabase/analysis.api'
import { useProviderConfigStatus } from '../hooks/useProviderSettings'
import { subscribeActionItemSyncStatus, unsubscribeChannel } from '../api/supabase/realtime'
import ConfidenceBadge from '../components/ConfidenceBadge'
import type { ActionItem, ActionItemPriority, ActionItemType, StatusUpdateProposal, WorkStatus } from '../types/supabase-models'
import { buildActionItemTree, ActionItemTreeNode } from '../hooks/supabase/actionItemTree'
import { Badge, Button, Card, EmptyState, Field, Icon, Input, Modal, Select, Toast as UiToast } from '../components/ui'

interface Props {
  onNavigate: (route: string) => void
  setBusy: (busy: boolean, text?: string) => void
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { variant: 'default' | 'warning' | 'success' | 'error'; label: string }> = {
    draft: { variant: 'default', label: 'Draft' },
    edited: { variant: 'warning', label: 'Edited' },
    approved: { variant: 'success', label: 'Approved' },
    rejected: { variant: 'error', label: 'Rejected' },
  }
  const s = map[status] ?? map.draft
  return <Badge variant={s.variant} size="sm">{s.label}</Badge>
}

function SyncBadge({ status, error: syncError }: { status: string; error?: string | null }) {
  const map: Record<string, { variant: 'default' | 'info' | 'success' | 'error'; icon: string; label: string }> = {
    pending: { variant: 'default', icon: 'schedule', label: 'Pending' },
    syncing: { variant: 'info', icon: 'sync', label: 'Syncing' },
    synced: { variant: 'success', icon: 'check_circle', label: 'Synced' },
    failed: { variant: 'error', icon: 'error', label: 'Failed' },
  }
  const s = map[status] ?? map.pending
  return (
    <Badge title={syncError || undefined} variant={s.variant} size="sm">
      <Icon name={s.icon} size={13} style={status === 'syncing' ? { animation: 'spin 0.8s linear infinite' } : undefined} />
      {s.label}
    </Badge>
  )
}

const WORK_STATUS_LABELS: Record<WorkStatus, string> = {
  todo: 'Todo',
  in_progress: 'In Progress',
  blocked: 'Blocked',
  done: 'Done',
  cancelled: 'Cancelled',
}

function isWorkStatus(value: unknown): value is WorkStatus {
  return typeof value === 'string' && value in WORK_STATUS_LABELS
}

function parseStatusUpdates(rawResponse: Record<string, unknown> | undefined): StatusUpdateProposal[] {
  const rawUpdates = rawResponse?.status_updates
  if (!Array.isArray(rawUpdates)) return []

  return rawUpdates.flatMap((item) => {
    if (!item || typeof item !== 'object') return []
    const row = item as Record<string, unknown>
    const matchedId = row.matched_action_item_id
    const oldStatus = row.old_status
    const newStatus = row.new_status

    if (typeof matchedId !== 'string' || !isWorkStatus(oldStatus) || !isWorkStatus(newStatus)) {
      return []
    }

    return [{
      matched_action_item_id: matchedId,
      matched_title: typeof row.matched_title === 'string' ? row.matched_title : 'Existing task',
      old_status: oldStatus,
      new_status: newStatus,
      evidence: typeof row.evidence === 'string' ? row.evidence : '',
      reason: typeof row.reason === 'string' ? row.reason : '',
      confidence: typeof row.confidence === 'number' ? row.confidence : 0,
    }]
  })
}

interface CardProps {
  item: ActionItem
  onToast: (msg: string, err?: boolean) => void
  syncOverride?: SyncOverride
}

type SyncOverride = Pick<ActionItem, 'sync_status' | 'sync_error' | 'jira_issue_key' | 'jira_issue_url'>

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
  const jiraIssueKey = syncOverride?.jira_issue_key ?? item.jira_issue_key
  const jiraIssueUrl = syncOverride?.jira_issue_url ?? item.jira_issue_url
  const isSynced = syncStatus === 'synced'

  const handleSave = useCallback(() => {
    if (isSynced) return
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
  }, [isSynced, item.id, editTitle, editAssignee, editDeadline, editPriority, editItem, onToast])

  const handleApprove = useCallback(() => {
    if (isSynced) return
    approve(item.id, {
      onError: (e) => onToast(`Lỗi approve: ${e.message}`, true),
    })
  }, [isSynced, item.id, approve, onToast])

  const handleReject = useCallback(() => {
    if (isSynced) return
    reject(item.id, {
      onError: (e) => onToast(`Lỗi reject: ${e.message}`, true),
    })
  }, [isSynced, item.id, reject, onToast])

  const actioning = isApproving || isRejecting

  return (
    <Card
      style={{
        padding: 14,
        marginBottom: 10,
        borderColor: isLowConfidence ? 'color-mix(in srgb, var(--color-warning) 45%, var(--color-border))' : undefined,
        background: isLowConfidence ? 'color-mix(in srgb, var(--color-warning) 8%, var(--color-surface))' : undefined,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8, flexWrap: 'wrap' }}>
        <Badge variant="primary" size="sm">{typeLabel}</Badge>
        <ConfidenceBadge confidence={item.confidence_score} />
        <StatusBadge status={item.review_status} />
        <SyncBadge status={syncStatus} error={syncError} />
        {jiraIssueKey && (
          <a
            href={jiraIssueUrl || undefined}
            onClick={(e) => {
              if (!jiraIssueUrl) e.preventDefault()
            }}
            style={{ color: 'var(--color-primary)', fontSize: 11, fontWeight: 800, textDecoration: 'none' }}
          >
            {jiraIssueKey}
          </a>
        )}
        <div style={{ flex: 1 }} />
        {!isEditing && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => setIsEditing(true)}
            disabled={isSynced}
            title={isSynced ? 'Item đã synced lên Jira nên không thể chỉnh sửa.' : undefined}
          >
            <Icon name="edit" size={14} /> Sửa
          </Button>
        )}
      </div>

      <div style={{ fontWeight: 800, fontSize: 14, color: 'var(--color-text-main)', marginBottom: 6 }}>
        {item.title}
      </div>

      {item.description && (
        <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 8, lineHeight: 1.5 }}>
          {item.description}
        </div>
      )}

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', fontSize: 11, color: 'var(--color-text-muted)', marginBottom: 8 }}>
        <span><Icon name="person" size={13} /> {item.assignee || 'TBD'}</span>
        <span><Icon name="event" size={13} /> {item.deadline || 'N/A'}</span>
        <span><Icon name="local_fire_department" size={13} /> {item.priority}</span>
      </div>

      {item.context && (
        <div style={{ fontSize: 11, color: 'var(--color-text-subtle)', fontStyle: 'italic', marginBottom: 8, lineHeight: 1.45 }}>
          <Icon name="format_quote" size={14} /> {item.context}
        </div>
      )}

      {isEditing && (
        <div style={{ marginTop: 10, padding: 12, background: 'var(--color-bg)', borderRadius: 'var(--radius-brand)', display: 'flex', flexDirection: 'column', gap: 10, border: '1px solid var(--color-border-subtle)' }}>
          <Field label="Title"><Input value={editTitle} onChange={(e) => setEditTitle(e.target.value)} placeholder="Title" /></Field>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 8 }}>
            <Field label="Assignee"><Input value={editAssignee} onChange={(e) => setEditAssignee(e.target.value)} placeholder="Assignee" /></Field>
            <Field label="Deadline"><Input value={editDeadline} onChange={(e) => setEditDeadline(e.target.value)} placeholder="YYYY-MM-DD" /></Field>
            <Field label="Priority">
              <Select value={editPriority} onChange={(e) => setEditPriority(e.target.value as ActionItemPriority)}>
                {['critical', 'high', 'medium', 'low'].map((p) => <option key={p} value={p}>{p}</option>)}
              </Select>
            </Field>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <Button size="sm" variant="primary" onClick={handleSave} disabled={isSaving || isSynced}>
              <Icon name="save" size={14} /> {isSaving ? 'Đang lưu...' : 'Lưu'}
            </Button>
            <Button size="sm" variant="outline" onClick={() => setIsEditing(false)}>Hủy</Button>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
        <Button size="sm" variant={item.review_status === 'approved' ? 'success' : 'outline'} onClick={handleApprove} disabled={isSynced || item.review_status === 'approved' || actioning}>
          <Icon name="check" size={14} /> Approve
        </Button>
        <Button size="sm" variant={item.review_status === 'rejected' ? 'danger' : 'outline'} onClick={handleReject} disabled={isSynced || item.review_status === 'rejected' || actioning}>
          <Icon name="close" size={14} /> Reject
        </Button>
      </div>
    </Card>
  )
})

function ActionItemTreeRenderer({
  node,
  onToast,
  syncOverrides,
}: {
  node: ActionItemTreeNode
  onToast: (msg: string, err?: boolean) => void
  syncOverrides: Record<string, SyncOverride>
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
            borderLeft: '2px dashed var(--color-border)',
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

type ManualItemType = Extract<ActionItemType, 'task' | 'subtask'>

interface AddManualItemDraft {
  item_type: ManualItemType
  parent_id: string | null
  title: string
  description: string
  assignee: string | null
}

function AddManualItemModal({
  tasks,
  isSaving,
  onClose,
  onSubmit,
}: {
  tasks: ActionItem[]
  isSaving: boolean
  onClose: () => void
  onSubmit: (draft: AddManualItemDraft) => void
}) {
  const [itemType, setItemType] = useState<ManualItemType>('task')
  const [parentId, setParentId] = useState('')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [assignee, setAssignee] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (itemType === 'subtask' && !parentId && tasks.length > 0) {
      setParentId(tasks[0].id)
    }
    if (itemType === 'task') {
      setParentId('')
    }
  }, [itemType, parentId, tasks])

  const handleSubmit = () => {
    const cleanTitle = title.trim()
    if (!cleanTitle) {
      setError('Title là bắt buộc.')
      return
    }
    if (itemType === 'subtask' && !parentId) {
      setError('Subtask cần chọn parent task.')
      return
    }

    onSubmit({
      item_type: itemType,
      parent_id: itemType === 'subtask' ? parentId : null,
      title: cleanTitle,
      description: description.trim(),
      assignee: assignee.trim() || null,
    })
  }

  return (
    <Modal
      open
      title="Add action item"
      onClose={isSaving ? undefined : onClose}
      footer={(
        <>
          <Button variant="outline" onClick={onClose} disabled={isSaving}>Hủy</Button>
          <Button variant="primary" onClick={handleSubmit} disabled={isSaving || (itemType === 'subtask' && tasks.length === 0)}>
            <Icon name="add" size={16} /> {isSaving ? 'Đang thêm...' : 'Add'}
          </Button>
        </>
      )}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <p style={{ margin: 0, fontSize: 13, color: 'var(--color-text-muted)' }}>Manual items are approved by default and ready to push.</p>
        <div style={{ display: 'grid', gridTemplateColumns: itemType === 'subtask' ? 'repeat(auto-fit, minmax(180px, 1fr))' : '1fr', gap: 10 }}>
          <Field label="Type">
            <Select value={itemType} onChange={(e) => setItemType(e.target.value as ManualItemType)}>
              <option value="task">Task</option>
              <option value="subtask">Subtask</option>
            </Select>
          </Field>
          {itemType === 'subtask' && (
            <Field label="Parent task">
              <Select value={parentId} onChange={(e) => setParentId(e.target.value)} disabled={tasks.length === 0}>
                {tasks.length === 0 ? (
                  <option value="">No task available</option>
                ) : (
                  tasks.map((task) => (
                    <option key={task.id} value={task.id}>
                      {task.jira_issue_key ? `${task.title} (${task.jira_issue_key})` : task.title}
                    </option>
                  ))
                )}
              </Select>
            </Field>
          )}
        </div>

        <Field label="Title" required><Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title" /></Field>
        <Field label="Description">
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Description"
            rows={4}
            style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-brand)', border: '1px solid var(--color-border)', background: 'var(--color-surface)', color: 'var(--color-text-main)', outline: 'none', resize: 'vertical', lineHeight: 1.45 }}
          />
        </Field>
        <Field label="Assignee"><Input value={assignee} onChange={(e) => setAssignee(e.target.value)} placeholder="Assignee" /></Field>

        {error && (
          <Card style={{ padding: 10, background: 'color-mix(in srgb, var(--color-danger) 10%, var(--color-surface))', color: 'var(--color-danger)', fontSize: 12 }}>
            {error}
          </Card>
        )}
      </div>
    </Modal>
  )
}

function SuggestedStatusUpdates({
  updates,
  isApplying,
  onApprove,
  onReject,
}: {
  updates: StatusUpdateProposal[]
  isApplying: boolean
  onApprove: (update: StatusUpdateProposal) => void
  onReject: (update: StatusUpdateProposal) => void
}) {
  if (updates.length === 0) return null

  return (
    <Card
      style={{
        padding: 14,
        marginBottom: 16,
        background: 'color-mix(in srgb, var(--color-primary) 6%, var(--color-surface))',
        borderColor: 'color-mix(in srgb, var(--color-primary) 28%, var(--color-border))',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <Icon name="published_with_changes" size={18} style={{ color: 'var(--color-primary)' }} />
        <div>
          <div style={{ fontWeight: 800, color: 'var(--color-text-main)', fontSize: 14 }}>Đề xuất cập nhật tiến độ</div>
          <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>AI chỉ đề xuất. Trạng thái chỉ đổi sau khi bạn approve.</div>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {updates.map((update) => {
          const key = `${update.matched_action_item_id}:${update.new_status}`
          return (
            <Card key={key} style={{ padding: 12, background: 'var(--color-surface)', borderColor: 'var(--color-border)' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: 260 }}>
                  <div style={{ fontWeight: 800, color: 'var(--color-text-main)', fontSize: 13, marginBottom: 6 }}>
                    {update.matched_title}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
                    <Badge variant="default" size="sm">{WORK_STATUS_LABELS[update.old_status]}</Badge>
                    <Icon name="arrow_forward" size={14} style={{ color: 'var(--color-text-muted)' }} />
                    <Badge variant={update.new_status === 'done' ? 'success' : update.new_status === 'blocked' ? 'warning' : 'info'} size="sm">
                      {WORK_STATUS_LABELS[update.new_status]}
                    </Badge>
                    <Badge variant="default" size="sm">{Math.round(update.confidence * 100)}%</Badge>
                  </div>
                  {update.evidence && (
                    <div style={{ fontSize: 12, color: 'var(--color-text-muted)', lineHeight: 1.45, marginBottom: 4 }}>
                      <strong>Evidence:</strong> {update.evidence}
                    </div>
                  )}
                  {update.reason && (
                    <div style={{ fontSize: 11, color: 'var(--color-text-subtle)', lineHeight: 1.45 }}>
                      {update.reason}
                    </div>
                  )}
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <Button size="sm" variant="success" onClick={() => onApprove(update)} disabled={isApplying}>
                    <Icon name="check" size={14} /> Approve update
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => onReject(update)} disabled={isApplying}>
                    <Icon name="close" size={14} /> Reject
                  </Button>
                </div>
              </div>
            </Card>
          )
        })}
      </div>
    </Card>
  )
}

function Toast({ msg, isError, onClose }: { msg: string; isError: boolean; onClose: () => void }) {
  useEffect(() => { const t = setTimeout(onClose, 3500); return () => clearTimeout(t) }, [onClose])
  return (
    <div style={{ position: 'fixed', bottom: 24, right: 24, zIndex: 999 }}>
      <UiToast type={isError ? 'error' : 'success'} title={isError ? 'Error' : 'Done'} message={msg} />
    </div>
  )
}

export default function ReviewView({ onNavigate, setBusy }: Props) {
  const { currentMeetingId } = useAppStore()

  const { data: items = [], isLoading, refetch } = useActionItemsList(currentMeetingId)
  const { data: analysisData } = useQuery({
    queryKey: ['reviewAnalysisResult', currentMeetingId],
    queryFn: () => getAnalysisResult(currentMeetingId!),
    enabled: !!currentMeetingId,
  })
  const jiraStatus = useProviderConfigStatus('jira')
  const { mutate: bulkApprove, isPending: approvingAll } = useBulkApproveActionItems(currentMeetingId)
  const { mutate: addManualItem, isPending: addingManualItem } = useAddManualActionItem(currentMeetingId)
  const { mutate: applyStatusUpdate, isPending: applyingStatusUpdate } = useApplyWorkStatusUpdate(currentMeetingId)

  const [toast, setToast] = useState<{ msg: string; isError: boolean } | null>(null)
  const [pushing, setPushing] = useState(false)
  const [showAddItemModal, setShowAddItemModal] = useState(false)
  const [syncOverrides, setSyncOverrides] = useState<Record<string, SyncOverride>>({})
  const [dismissedStatusUpdates, setDismissedStatusUpdates] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (!currentMeetingId) return

    const channel = subscribeActionItemSyncStatus(currentMeetingId, (update) => {
      setSyncOverrides((prev) => ({
        ...prev,
        [update.id]: {
          sync_status: update.sync_status,
          sync_error: update.sync_error,
          jira_issue_key: update.jira_issue_key,
          jira_issue_url: update.jira_issue_url,
        },
      }))
    })

    return () => { unsubscribeChannel(channel) }
  }, [currentMeetingId])

  const showToast = useCallback((msg: string, isError = false) => {
    setToast({ msg, isError })
  }, [])

  const statusUpdates = useMemo(() => {
    const updates = parseStatusUpdates(analysisData?.analysis_result?.raw_response)
    return updates.filter((update) => {
      const key = `${update.matched_action_item_id}:${update.new_status}`
      return !dismissedStatusUpdates.has(key)
    })
  }, [analysisData?.analysis_result?.raw_response, dismissedStatusUpdates])

  const effectiveItems = useMemo(
    () => items.map((item) => ({ ...item, ...syncOverrides[item.id] })),
    [items, syncOverrides]
  )

  const summary = useMemo(() => {
    const total = effectiveItems.length
    const approved = effectiveItems.filter((i) => i.review_status === 'approved').length
    const rejected = effectiveItems.filter((i) => i.review_status === 'rejected').length
    const flagged = effectiveItems.filter((i) => i.confidence_score < 0.6 && i.review_status === 'draft').length
    const pending = effectiveItems.filter((i) => i.review_status === 'draft' || i.review_status === 'edited').length
    const syncing = effectiveItems.filter((i) => i.sync_status === 'syncing').length
    const synced = effectiveItems.filter((i) => i.sync_status === 'synced').length
    const failed = effectiveItems.filter((i) => i.sync_status === 'failed').length
    const ready = effectiveItems.filter((i) => i.review_status === 'approved' && i.sync_status === 'pending').length
    const pushableApproved = effectiveItems.filter((i) => i.review_status === 'approved' && i.sync_status !== 'synced' && i.sync_status !== 'syncing').length
    return { total, approved, rejected, flagged, pending, syncing, synced, failed, ready, pushableApproved }
  }, [effectiveItems])

  const handleApproveAll = useCallback(() => {
    bulkApprove(undefined, {
      onSuccess: (result) => showToast(`Đã approve ${result.approved_count} items.`),
      onError: (e) => showToast(`Lỗi: ${e.message}`, true),
    })
  }, [bulkApprove, showToast])

  const handlePushJira = useCallback(async () => {
    setPushing(true)
    setBusy(true, 'Đang push lên Jira...')
    try {
      await pushToJira(currentMeetingId!)
      await refetch()
      showToast('Đã hoàn tất push Jira. Kiểm tra trạng thái từng item.')
    } catch (e) {
      showToast(`Lỗi push Jira: ${e instanceof Error ? e.message : e}`, true)
    } finally {
      setPushing(false)
      setBusy(false)
    }
  }, [currentMeetingId, refetch, setBusy, showToast])

  const handleAddManualItem = useCallback((draft: AddManualItemDraft) => {
    if (!currentMeetingId) return

    addManualItem(
      {
        meeting_id: currentMeetingId,
        parent_id: draft.parent_id,
        item_type: draft.item_type,
        title: draft.title,
        description: draft.description,
        assignee: draft.assignee,
        priority: 'medium',
        context: 'Manual item',
        confidence_score: 1.0,
        review_status: 'approved',
        is_selected: true,
        sync_status: 'pending',
      },
      {
        onSuccess: () => {
          setShowAddItemModal(false)
          showToast('Đã thêm action item.')
        },
        onError: (e) => showToast(`Lỗi thêm item: ${e.message}`, true),
      }
    )
  }, [addManualItem, currentMeetingId, showToast])

  const dismissStatusUpdate = useCallback((update: StatusUpdateProposal) => {
    const key = `${update.matched_action_item_id}:${update.new_status}`
    setDismissedStatusUpdates((prev) => new Set(prev).add(key))
  }, [])

  const handleApproveStatusUpdate = useCallback((update: StatusUpdateProposal) => {
    applyStatusUpdate(
      {
        itemId: update.matched_action_item_id,
        work_status: update.new_status,
        note: update.evidence || update.reason || undefined,
      },
      {
        onSuccess: () => {
          dismissStatusUpdate(update)
          showToast(`Đã cập nhật tiến độ: ${update.matched_title}`)
        },
        onError: (e) => showToast(`Lỗi cập nhật tiến độ: ${e.message}`, true),
      }
    )
  }, [applyStatusUpdate, dismissStatusUpdate, showToast])

  const handleRejectStatusUpdate = useCallback((update: StatusUpdateProposal) => {
    dismissStatusUpdate(update)
    showToast(`Đã bỏ qua đề xuất: ${update.matched_title}`)
  }, [dismissStatusUpdate, showToast])

  const pushBlockReason = useMemo(() => {
    if (!jiraStatus.data?.is_configured) return 'Chưa cấu hình Jira. Hãy vào Settings > Jira để lưu Base URL, email, API token và project key.'
    if (summary.pending > 0) return `Còn ${summary.pending} item cần approve hoặc reject trước khi push.`
    if (summary.approved === 0) return 'Cần approve ít nhất 1 item để push lên Jira.'
    if (summary.pushableApproved === 0) return 'Tất cả item đã approve đã được sync lên Jira.'
    return null
  }, [jiraStatus.data?.is_configured, summary.approved, summary.pending, summary.pushableApproved])
  const pushDisabled = Boolean(pushBlockReason) || pushing || jiraStatus.isLoading
  const treeNodes = buildActionItemTree(items)
  const parentTaskOptions = useMemo(
    () => effectiveItems.filter((item) => item.item_type === 'task'),
    [effectiveItems]
  )

  if (!currentMeetingId) {
    return <Card><EmptyState icon="rule" title="Không có meeting nào được chọn" description="Chọn một meeting để review action items." /></Card>
  }

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      {toast && <Toast msg={toast.msg} isError={toast.isError} onClose={() => setToast(null)} />}
      {showAddItemModal && (
        <AddManualItemModal
          tasks={parentTaskOptions}
          isSaving={addingManualItem}
          onClose={() => setShowAddItemModal(false)}
          onSubmit={handleAddManualItem}
        />
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16, gap: 16, flexWrap: 'wrap' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <Icon name="rule" size={22} style={{ color: 'var(--color-primary)' }} />
            <h2 style={{ fontSize: 22, fontWeight: 800, color: 'var(--color-text-main)', margin: 0 }}>
              Review action items
            </h2>
          </div>
          <p style={{ fontSize: 13, color: 'var(--color-text-muted)', margin: 0 }}>
            Approve hoặc reject từng item trước khi push lên Jira.
          </p>
        </div>
        <Button variant="outline" onClick={() => onNavigate('results')}><Icon name="arrow_back" size={16} /> Back</Button>
      </div>

      <Card style={{ padding: 14, marginBottom: 12, background: 'color-mix(in srgb, var(--color-primary) 7%, var(--color-surface))' }}>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', fontSize: 12, color: 'var(--color-primary)', fontWeight: 800 }}>
          <span>Tổng: {summary.total}</span>
          <span>Approved: {summary.approved}</span>
          <span>Rejected: {summary.rejected}</span>
          <span>Cần xem: {summary.flagged}</span>
          <span>Chờ: {summary.pending}</span>
        </div>
      </Card>

      <Card
        style={{
          padding: 14,
          marginBottom: 12,
          background: pushBlockReason ? 'color-mix(in srgb, var(--color-warning) 8%, var(--color-surface))' : 'color-mix(in srgb, var(--color-success) 8%, var(--color-surface))',
          borderColor: pushBlockReason ? 'color-mix(in srgb, var(--color-warning) 35%, var(--color-border))' : 'color-mix(in srgb, var(--color-success) 35%, var(--color-border))',
          color: pushBlockReason ? 'var(--color-warning)' : 'var(--color-success)',
        }}
      >
        <div style={{ fontSize: 12, lineHeight: 1.5, fontWeight: 700 }}>
          <div>Synced: {summary.synced} | Ready: {summary.ready} | Failed: {summary.failed} | Syncing: {summary.syncing}</div>
          <div>
            {pushBlockReason
              ? `Chưa thể push: ${pushBlockReason}`
              : `Sẵn sàng push/retry ${summary.pushableApproved} item đã approve lên Jira.`}
          </div>
        </div>
      </Card>

      <SuggestedStatusUpdates
        updates={statusUpdates}
        isApplying={applyingStatusUpdate}
        onApprove={handleApproveStatusUpdate}
        onReject={handleRejectStatusUpdate}
      />

      <div style={{ display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap' }}>
        <Button variant="outline" onClick={() => setShowAddItemModal(true)}><Icon name="add" size={16} /> Add Task</Button>
        <Button variant="success" onClick={handleApproveAll} disabled={approvingAll}>
          <Icon name="done_all" size={16} /> {approvingAll ? 'Đang approve...' : 'Approve all'}
        </Button>
        <Button variant="primary" onClick={handlePushJira} disabled={pushDisabled} title={pushBlockReason || undefined}>
          <Icon name={pushing ? 'progress_activity' : 'rocket_launch'} size={16} style={pushing ? { animation: 'spin 0.8s linear infinite' } : undefined} />
          {pushing ? 'Đang push...' : 'Push to Jira'}
        </Button>
      </div>

      {isLoading ? (
        <Card style={{ padding: 24, color: 'var(--color-text-muted)', fontSize: 13, display: 'flex', alignItems: 'center', gap: 10 }}>
          <Icon name="progress_activity" size={20} style={{ color: 'var(--color-primary)', animation: 'spin 0.8s linear infinite' }} />
          Đang tải...
        </Card>
      ) : treeNodes.length > 0 ? (
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
        <Card><EmptyState icon="task_alt" title="Không có items để review" description="Action items sẽ xuất hiện sau khi meeting được phân tích." /></Card>
      )}
    </div>
  )
}

