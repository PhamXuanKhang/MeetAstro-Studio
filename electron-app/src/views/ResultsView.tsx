import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAppStore } from '../store/appStore'
import ConfidenceBadge from '../components/ConfidenceBadge'
import StatusBadge from '../components/StatusBadge'
import { pushToJira } from '../api/jira'
import { addManualActionItem, approveActionItem, editActionItem, rejectActionItem } from '../api/supabase/actionItem.api'
import { getJiraIssueLinks } from '../api/supabase/jiraSync.api'
import { getMeetingDetail } from '../api/supabase/meetings.api'
import { subscribeActionItemSyncStatus, unsubscribeChannel } from '../api/supabase/realtime'
import type { RealtimeChannel } from '@supabase/supabase-js'
import type {
  ActionItem,
  ActionItemPriority,
  ActionItemType,
  AnalysisResult,
  JiraIssueLink,
  Meeting,
  SyncStatus,
  TranscriptSegment,
} from '../types/supabase-models'

interface Props {
  onNavigate?: (route: string) => void
}

type DetailTab = 'summary' | 'transcript' | 'action_items'

type ActionItemNode = ActionItem & { children: ActionItemNode[] }

interface EditDraft {
  id: string
  title: string
  description: string
  context: string
  assignee: string
  deadline: string
  priority: ActionItemPriority
}

interface AddDraft {
  parent_id: string | null
  item_type: ActionItemType
  title: string
  description: string
  context: string
  assignee: string
  deadline: string
  priority: ActionItemPriority
}

const UI = {
  primary: '#5645d4',
  primaryPressed: '#4534b3',
  ink: '#1a1a1a',
  charcoal: '#37352f',
  slate: '#5d5b54',
  steel: '#787671',
  muted: '#bbb8b1',
  canvas: '#ffffff',
  surface: '#f6f5f4',
  surfaceSoft: '#fafaf9',
  hairline: '#e5e3df',
  hairlineStrong: '#c8c4be',
  lavender: '#e6e0f5',
  peach: '#ffe8d4',
  mint: '#d9f3e1',
  sky: '#dcecfa',
  warning: '#dd5b00',
  error: '#e03131',
  success: '#1aae39',
  font: "'Notion Sans', Inter, -apple-system, system-ui, 'Segoe UI', Helvetica, sans-serif",
}

const SPEAKER_COLORS = [
  '#5645d4', '#7b3ff2', '#2a9d99', '#dd5b00', '#ff64c8',
  '#1aae39', '#0075de', '#523410', '#a02e6d', '#391c57',
]

const btnBase: React.CSSProperties = {
  padding: '10px 18px',
  borderRadius: 8,
  border: 'none',
  fontWeight: 500,
  fontSize: 14,
  cursor: 'pointer',
  fontFamily: UI.font,
}

const cardStyle: React.CSSProperties = {
  background: UI.canvas,
  border: `1px solid ${UI.hairline}`,
  borderRadius: 12,
  padding: 24,
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  minHeight: 44,
  padding: '12px 16px',
  borderRadius: 8,
  border: `1px solid ${UI.hairlineStrong}`,
  background: UI.canvas,
  color: UI.ink,
  fontFamily: UI.font,
  fontSize: 14,
  boxSizing: 'border-box',
}

function speakerColor(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = (hash * 31 + name.charCodeAt(i)) & 0xffffffff
  return SPEAKER_COLORS[Math.abs(hash) % SPEAKER_COLORS.length]
}

function fmtTime(s: number): string {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

function fmtDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString('vi-VN', {
      day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function buildActionItemTree(items: ActionItem[]): ActionItemNode[] {
  const seenIds = new Set<string>()
  const byId = new Map<string, ActionItemNode>()
  const roots: ActionItemNode[] = []

  for (const item of items) {
    if (!item.id || seenIds.has(item.id)) continue
    seenIds.add(item.id)
    byId.set(item.id, { ...item, children: [] })
  }

  function hasCycle(nodeId: string, parentId: string | null): boolean {
    const visited = new Set<string>([nodeId])
    let cursor = parentId
    while (cursor) {
      if (visited.has(cursor)) return true
      visited.add(cursor)
      cursor = byId.get(cursor)?.parent_id ?? null
    }
    return false
  }

  for (const node of byId.values()) {
    const parent = node.parent_id ? byId.get(node.parent_id) : null
    if (parent && !hasCycle(node.id, node.parent_id)) {
      parent.children.push(node)
    } else {
      roots.push(node)
    }
  }

  return roots
}

function findItem(items: ActionItem[], itemId: string): ActionItem | null {
  return items.find((item) => item.id === itemId) ?? null
}

function syncLabel(status: SyncStatus): string {
  return {
    pending: 'Pending',
    syncing: 'Syncing',
    synced: 'Synced',
    failed: 'Failed',
  }[status]
}

function syncStyle(status: SyncStatus): React.CSSProperties {
  const map: Record<SyncStatus, React.CSSProperties> = {
    pending: { background: UI.surface, color: UI.steel },
    syncing: { background: UI.sky, color: '#005bab' },
    synced: { background: UI.mint, color: UI.success },
    failed: { background: '#ffe1e1', color: UI.error },
  }
  return map[status]
}

function typeBadgeColor(type: ActionItemType): React.CSSProperties {
  const map: Record<ActionItemType, React.CSSProperties> = {
    epic: { background: UI.lavender, color: '#391c57' },
    task: { background: UI.peach, color: '#793400' },
    subtask: { background: UI.mint, color: UI.success },
  }
  return map[type]
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div style={{ ...cardStyle, textAlign: 'center', color: UI.steel }}>
      <div style={{ fontWeight: 600, fontSize: 16, color: UI.charcoal, marginBottom: 6 }}>{title}</div>
      <div style={{ fontSize: 14, lineHeight: 1.5 }}>{description}</div>
    </div>
  )
}

function Modal({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div style={{ background: UI.canvas, borderRadius: 12, padding: 24, width: 'min(720px, 100%)', maxHeight: '90vh', overflowY: 'auto', boxShadow: 'rgba(15, 15, 15, 0.16) 0px 16px 48px -8px', border: `1px solid ${UI.hairline}` }}>
        {children}
      </div>
    </div>
  )
}

function SummaryTab({ analysis }: { analysis: AnalysisResult | null }) {
  if (!analysis) {
    return <EmptyState title="Chưa có summary" description="Meeting này chưa có kết quả analysis để hiển thị." />
  }

  return (
    <div style={{ display: 'grid', gap: 14 }}>
      <section style={cardStyle}>
        <h3 style={{ margin: '0 0 10px', fontSize: 18, fontWeight: 600, color: UI.ink }}>Tóm tắt cuộc họp</h3>
        <p style={{ margin: 0, fontSize: 14, color: UI.charcoal, lineHeight: 1.65 }}>{analysis.summary_text || 'Không có summary.'}</p>
      </section>

      <section style={cardStyle}>
        <h3 style={{ margin: '0 0 10px', fontSize: 18, fontWeight: 600, color: UI.ink }}>Quyết định chính</h3>
        {analysis.key_decisions?.length ? (
          <ul style={{ margin: 0, paddingLeft: 20, display: 'grid', gap: 8, color: UI.charcoal, fontSize: 14, lineHeight: 1.55 }}>
            {analysis.key_decisions.map((item, i) => <li key={i}>{item}</li>)}
          </ul>
        ) : (
          <p style={{ margin: 0, color: UI.steel, fontSize: 14 }}>Không có quyết định chính.</p>
        )}
      </section>

      <section style={cardStyle}>
        <h3 style={{ margin: '0 0 10px', fontSize: 18, fontWeight: 600, color: UI.ink }}>Parking lot</h3>
        {analysis.parking_lot?.length ? (
          <ul style={{ margin: 0, paddingLeft: 20, display: 'grid', gap: 8, color: UI.charcoal, fontSize: 14, lineHeight: 1.55 }}>
            {analysis.parking_lot.map((item, i) => <li key={i}>{item}</li>)}
          </ul>
        ) : (
          <p style={{ margin: 0, color: UI.steel, fontSize: 14 }}>Không có parking lot.</p>
        )}
      </section>
    </div>
  )
}

function TranscriptTab({ segments, onChange }: { segments: TranscriptSegment[]; onChange: (segments: TranscriptSegment[]) => void }) {
  if (segments.length === 0) {
    return <EmptyState title="Chưa có transcript" description="Meeting này chưa có transcript segments để hiển thị." />
  }

  const updateSegment = (id: string, content: string) => {
    onChange(segments.map((segment) => segment.id === id ? { ...segment, content } : segment))
  }

  return (
    <div style={{ display: 'grid', gap: 10 }}>
      {segments.map((segment) => {
        const color = speakerColor(segment.speaker)
        return (
          <div key={segment.id} style={{ ...cardStyle, padding: 16, display: 'flex', gap: 14 }}>
            <div style={{ minWidth: 112, display: 'flex', flexDirection: 'column', gap: 6 }}>
              <span style={{ width: 'fit-content', padding: '4px 10px', borderRadius: 999, background: `${color}22`, color, fontSize: 12, fontWeight: 700 }}>
                {segment.speaker}
              </span>
              <span style={{ fontSize: 12, color: UI.steel, fontVariantNumeric: 'tabular-nums' }}>
                {fmtTime(segment.start_time)} – {fmtTime(segment.end_time)}
              </span>
            </div>
            <textarea
              value={segment.content}
              onChange={(e) => updateSegment(segment.id, e.target.value)}
              rows={Math.max(2, Math.ceil(segment.content.length / 90))}
              style={{ ...inputStyle, flex: 1, minHeight: 70, resize: 'vertical', lineHeight: 1.55 }}
            />
          </div>
        )
      })}
    </div>
  )
}

function ActionItemCard({
  node,
  depth,
  collapsed,
  onToggleCollapse,
  onToggleSelected,
  onEdit,
  onApprove,
  onReject,
}: {
  node: ActionItemNode
  depth: number
  collapsed: Set<string>
  onToggleCollapse: (id: string) => void
  onToggleSelected: (item: ActionItem) => void
  onEdit: (item: ActionItem) => void
  onApprove: (item: ActionItem) => void
  onReject: (item: ActionItem) => void
}) {
  const hasChildren = node.children.length > 0
  const isCollapsed = collapsed.has(node.id)
  const eligible = node.review_status === 'approved' && node.is_selected

  return (
    <div style={{ display: 'grid', gap: 8 }}>
      <div style={{ ...cardStyle, padding: 16, marginLeft: depth * 26, borderColor: eligible ? UI.primary : UI.hairline }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 10, flexWrap: 'wrap' }}>
          <button
            onClick={() => hasChildren && onToggleCollapse(node.id)}
            disabled={!hasChildren}
            style={{ border: `1px solid ${UI.hairline}`, background: UI.surfaceSoft, borderRadius: 6, width: 28, height: 28, cursor: hasChildren ? 'pointer' : 'default', color: hasChildren ? UI.ink : UI.muted }}
          >
            {hasChildren ? (isCollapsed ? '+' : '−') : '·'}
          </button>
          <input type="checkbox" checked={node.is_selected} onChange={() => onToggleSelected(node)} />
          <span style={{ ...typeBadgeColor(node.item_type), padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700, textTransform: 'uppercase' }}>
            {node.item_type}
          </span>
          <ConfidenceBadge confidence={node.confidence_score} />
          <StatusBadge status={node.review_status} />
          <span style={{ ...syncStyle(node.sync_status), padding: '2px 8px', borderRadius: 6, fontSize: 11, fontWeight: 700 }}>
            {syncLabel(node.sync_status)}
          </span>
          <div style={{ flex: 1 }} />
          <button onClick={() => onEdit(node)} style={{ ...btnBase, padding: '7px 12px', background: UI.canvas, color: UI.ink, border: `1px solid ${UI.hairlineStrong}` }}>Sửa</button>
          <button onClick={() => onApprove(node)} style={{ ...btnBase, padding: '7px 12px', background: UI.mint, color: UI.success }}>Approve</button>
          <button onClick={() => onReject(node)} style={{ ...btnBase, padding: '7px 12px', background: '#ffe1e1', color: UI.error }}>Reject</button>
        </div>
        <div style={{ fontWeight: 700, color: UI.ink, fontSize: 15, marginBottom: 6 }}>{node.title}</div>
        {node.description && <div style={{ color: UI.charcoal, fontSize: 13, lineHeight: 1.5, marginBottom: 8 }}>{node.description}</div>}
        <div style={{ color: UI.slate, fontSize: 12, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <span>Assignee: {node.assignee || 'TBD'}</span>
          <span>Deadline: {node.deadline || 'N/A'}</span>
          <span>Priority: {node.priority}</span>
          {node.jira_issue_key && node.jira_issue_url && <a href={node.jira_issue_url} target="_blank" rel="noreferrer" style={{ color: '#0075de' }}>{node.jira_issue_key}</a>}
        </div>
        {node.sync_error && <div style={{ marginTop: 8, color: UI.error, fontSize: 12 }}>{node.sync_error}</div>}
      </div>
      {!isCollapsed && node.children.map((child) => (
        <ActionItemCard
          key={child.id}
          node={child}
          depth={depth + 1}
          collapsed={collapsed}
          onToggleCollapse={onToggleCollapse}
          onToggleSelected={onToggleSelected}
          onEdit={onEdit}
          onApprove={onApprove}
          onReject={onReject}
        />
      ))}
    </div>
  )
}

export default function ResultsView({ onNavigate }: Props) {
  const {
    currentMeetingId,
    meetingDetailTab,
    setMeetingDetailTab,
    setMeetingDetail,
    setMeetingAnalysisResult,
    setMeetingActionItems,
    setMeetingTranscriptSegments,
  } = useAppStore()

  const [meeting, setMeeting] = useState<Meeting | null>(null)
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [segments, setSegments] = useState<TranscriptSegment[]>([])
  const [items, setItems] = useState<ActionItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())
  const [editDraft, setEditDraft] = useState<EditDraft | null>(null)
  const [addDraft, setAddDraft] = useState<AddDraft | null>(null)
  const [saving, setSaving] = useState(false)
  const [pushFeed, setPushFeed] = useState<string[]>([])
  const [pushProgress, setPushProgress] = useState(0)
  const [pushing, setPushing] = useState(false)
  const [jiraLinks, setJiraLinks] = useState<JiraIssueLink[]>([])
  const [pushError, setPushError] = useState<string | null>(null)

  const loadDetail = useCallback(async () => {
    if (!currentMeetingId) return
    setLoading(true)
    setError(null)
    try {
      const result = await getMeetingDetail(currentMeetingId)
      setMeeting(result.data.meeting)
      setAnalysis(result.data.analysis_result)
      setSegments(result.data.transcript_segments)
      setItems(result.data.action_items)
      setMeetingDetail(result.data.meeting)
      setMeetingAnalysisResult(result.data.analysis_result)
      setMeetingTranscriptSegments(result.data.transcript_segments)
      setMeetingActionItems(result.data.action_items)
      const links = await getJiraIssueLinks(currentMeetingId).catch(() => ({ data: { items: [] } }))
      setJiraLinks(links.data.items)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [currentMeetingId, setMeetingActionItems, setMeetingAnalysisResult, setMeetingDetail, setMeetingTranscriptSegments])

  useEffect(() => {
    loadDetail()
  }, [loadDetail])

  useEffect(() => {
    if (!currentMeetingId) return undefined
    let channel: RealtimeChannel | null = null
    try {
      channel = subscribeActionItemSyncStatus(currentMeetingId, (update) => {
        setItems((prev) => prev.map((item) => item.id === update.id ? { ...item, sync_status: update.sync_status, sync_error: update.sync_error } : item))
        setPushFeed((prev) => [`${update.id}: ${syncLabel(update.sync_status)}`, ...prev].slice(0, 8))
      })
    } catch {
      channel = null
    }
    return () => { void unsubscribeChannel(channel) }
  }, [currentMeetingId])

  const tree = useMemo(() => buildActionItemTree(items), [items])
  const epics = useMemo(() => items.filter((item) => item.item_type === 'epic'), [items])
  const eligibleItems = useMemo(() => items.filter((item) => item.review_status === 'approved' && item.is_selected), [items])
  const failedItems = useMemo(() => items.filter((item) => item.sync_status === 'failed'), [items])

  const setItemsAndStore = useCallback((next: ActionItem[]) => {
    setItems(next)
    setMeetingActionItems(next)
  }, [setMeetingActionItems])

  const toggleSelected = useCallback(async (item: ActionItem) => {
    const nextValue = !item.is_selected
    const optimistic = items.map((candidate) => candidate.id === item.id ? { ...candidate, is_selected: nextValue } : candidate)
    setItemsAndStore(optimistic)
    try {
      await editActionItem({ action_item_id: item.id, is_selected: nextValue })
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setItemsAndStore(items)
    }
  }, [items, setItemsAndStore])

  const handleApprove = useCallback(async (item: ActionItem) => {
    const optimistic = items.map((candidate) => candidate.id === item.id ? { ...candidate, review_status: 'approved' as const, is_selected: true } : candidate)
    setItemsAndStore(optimistic)
    try {
      await approveActionItem({ action_item_id: item.id, review_status: 'approved', is_selected: true })
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setItemsAndStore(items)
    }
  }, [items, setItemsAndStore])

  const handleReject = useCallback(async (item: ActionItem) => {
    const optimistic = items.map((candidate) => candidate.id === item.id ? { ...candidate, review_status: 'rejected' as const, is_selected: false } : candidate)
    setItemsAndStore(optimistic)
    try {
      await rejectActionItem({ action_item_id: item.id, review_status: 'rejected', is_selected: false })
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setItemsAndStore(items)
    }
  }, [items, setItemsAndStore])

  const openEdit = (item: ActionItem) => setEditDraft({
    id: item.id,
    title: item.title,
    description: item.description,
    context: item.context,
    assignee: item.assignee ?? '',
    deadline: item.deadline ?? '',
    priority: item.priority,
  })

  const saveEdit = async () => {
    if (!editDraft) return
    setSaving(true)
    try {
      await editActionItem({
        action_item_id: editDraft.id,
        title: editDraft.title,
        description: editDraft.description,
        context: editDraft.context,
        assignee: editDraft.assignee || null,
        deadline: editDraft.deadline || null,
        priority: editDraft.priority,
        review_status: 'edited',
      })
      const next = items.map((item) => item.id === editDraft.id ? {
        ...item,
        title: editDraft.title,
        description: editDraft.description,
        context: editDraft.context,
        assignee: editDraft.assignee || null,
        deadline: editDraft.deadline || null,
        priority: editDraft.priority,
        review_status: 'edited' as const,
      } : item)
      setItemsAndStore(next)
      setEditDraft(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  const saveAdd = async () => {
    if (!addDraft || !currentMeetingId || !addDraft.title.trim()) return
    setSaving(true)
    try {
      const result = await addManualActionItem({
        meeting_id: currentMeetingId,
        parent_id: addDraft.parent_id,
        item_type: addDraft.item_type,
        title: addDraft.title,
        description: addDraft.description,
        assignee: addDraft.assignee || null,
        deadline: addDraft.deadline || null,
        priority: addDraft.priority,
        context: addDraft.context || 'Manual item',
        confidence_score: 1,
        review_status: 'edited',
        is_selected: false,
        sync_status: 'pending',
      })
      const now = new Date().toISOString()
      const nextItem: ActionItem = {
        id: result.data.action_item.id,
        meeting_id: currentMeetingId,
        parent_id: addDraft.parent_id,
        item_type: addDraft.item_type,
        title: addDraft.title,
        description: addDraft.description,
        assignee: addDraft.assignee || null,
        deadline: addDraft.deadline || null,
        priority: addDraft.priority,
        context: addDraft.context || 'Manual item',
        confidence_score: 1,
        review_status: 'edited',
        is_selected: false,
        sync_status: 'pending',
        sync_error: null,
        jira_issue_key: null,
        jira_issue_url: null,
        created_at: now,
        updated_at: now,
      }
      setItemsAndStore([...items, nextItem])
      setAddDraft(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSaving(false)
    }
  }

  const runPush = async () => {
    if (!currentMeetingId || eligibleItems.length === 0) return
    setPushing(true)
    setPushError(null)
    setPushProgress(10)
    setPushFeed([`Queued ${eligibleItems.length} selected approved item(s).`])
    try {
      setPushProgress(35)
      await pushToJira(currentMeetingId)
      setPushProgress(75)
      setPushFeed((prev) => ['Push job completed. Refreshing Jira links...', ...prev])
      await loadDetail()
      const links = await getJiraIssueLinks(currentMeetingId).catch(() => ({ data: { items: [] } }))
      setJiraLinks(links.data.items)
      setPushProgress(100)
      setPushFeed((prev) => [`Loaded ${links.data.items.length} Jira link(s).`, ...prev])
    } catch (e) {
      setPushError(e instanceof Error ? e.message : String(e))
      setPushFeed((prev) => ['Push failed. Use Retry after checking failed items.', ...prev])
    } finally {
      setPushing(false)
    }
  }

  if (!currentMeetingId) {
    return <EmptyState title="Chưa chọn meeting" description="Chọn một meeting từ History hoặc tạo meeting mới để xem chi tiết." />
  }

  return (
    <div style={{ maxWidth: 1120, margin: '0 auto', fontFamily: UI.font, color: UI.ink }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, marginBottom: 20 }}>
        <div>
          <h2 style={{ margin: '0 0 6px', fontSize: 22, fontWeight: 600, color: UI.ink }}>{meeting?.title || 'Meeting Detail'}</h2>
          <p style={{ margin: 0, color: UI.slate, fontSize: 14 }}>
            {meeting ? `${meeting.status} · ${fmtDate(meeting.updated_at)}` : 'Loading meeting detail...'}
          </p>
        </div>
        <button onClick={() => onNavigate?.('history')} style={{ ...btnBase, background: UI.canvas, color: UI.ink, border: `1px solid ${UI.hairlineStrong}` }}>
          Back to History
        </button>
      </div>

      <div style={{ display: 'flex', gap: 8, borderBottom: `1px solid ${UI.hairline}`, marginBottom: 20 }}>
        {([
          ['summary', 'Summary'],
          ['transcript', 'Transcript'],
          ['action_items', 'Action Items'],
        ] as [DetailTab, string][]).map(([tab, label]) => (
          <button
            key={tab}
            onClick={() => setMeetingDetailTab(tab)}
            style={{
              background: 'transparent',
              color: meetingDetailTab === tab ? UI.ink : UI.steel,
              border: 0,
              borderBottom: `2px solid ${meetingDetailTab === tab ? UI.ink : 'transparent'}`,
              padding: '12px 16px',
              fontWeight: 500,
              cursor: 'pointer',
              fontFamily: UI.font,
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {error && <div style={{ ...cardStyle, marginBottom: 14, color: UI.error, background: '#fff5f5' }}>{error}</div>}
      {loading ? (
        <div style={{ ...cardStyle, color: UI.steel }}>Đang tải meeting detail...</div>
      ) : (
        <>
          {meetingDetailTab === 'summary' && <SummaryTab analysis={analysis} />}
          {meetingDetailTab === 'transcript' && <TranscriptTab segments={segments} onChange={(next) => { setSegments(next); setMeetingTranscriptSegments(next) }} />}
          {meetingDetailTab === 'action_items' && (
            <div style={{ display: 'grid', gap: 14 }}>
              <div style={{ ...cardStyle, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                <div>
                  <h3 style={{ margin: '0 0 4px', fontSize: 18 }}>Action Items</h3>
                  <p style={{ margin: 0, color: UI.slate, fontSize: 13 }}>{eligibleItems.length} selected approved item(s) ready to push.</p>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    onClick={() => setAddDraft({ parent_id: epics[0]?.id ?? null, item_type: 'task', title: '', description: '', context: '', assignee: '', deadline: '', priority: 'medium' })}
                    style={{ ...btnBase, background: UI.canvas, color: UI.ink, border: `1px solid ${UI.hairlineStrong}` }}
                  >
                    Add Task
                  </button>
                  <button
                    onClick={runPush}
                    disabled={eligibleItems.length === 0 || pushing}
                    style={{ ...btnBase, background: eligibleItems.length === 0 || pushing ? UI.hairline : UI.primary, color: eligibleItems.length === 0 || pushing ? UI.muted : '#fff', cursor: eligibleItems.length === 0 || pushing ? 'not-allowed' : 'pointer' }}
                  >
                    {pushing ? 'Pushing...' : 'Push to Jira'}
                  </button>
                </div>
              </div>

              {(pushFeed.length > 0 || jiraLinks.length > 0 || failedItems.length > 0 || pushError) && (
                <div style={cardStyle}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                    <strong>Push progress</strong>
                    <span style={{ color: UI.steel, fontSize: 13 }}>{pushProgress}%</span>
                  </div>
                  <div style={{ height: 8, background: UI.surface, borderRadius: 999, overflow: 'hidden', marginBottom: 12 }}>
                    <div style={{ height: '100%', width: `${pushProgress}%`, background: UI.primary }} />
                  </div>
                  {pushError && <div style={{ color: UI.error, fontSize: 13, marginBottom: 8 }}>{pushError}</div>}
                  {pushFeed.map((line, i) => <div key={`${line}-${i}`} style={{ color: UI.slate, fontSize: 13, marginBottom: 4 }}>{line}</div>)}
                  {jiraLinks.length > 0 && (
                    <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      {jiraLinks.map((link) => <a key={link.id} href={link.jira_issue_url} target="_blank" rel="noreferrer" style={{ color: '#0075de', fontWeight: 600 }}>{link.jira_issue_key}</a>)}
                    </div>
                  )}
                  {failedItems.length > 0 && (
                    <div style={{ marginTop: 12 }}>
                      <strong style={{ color: UI.error }}>Failed items</strong>
                      {failedItems.map((item) => <div key={item.id} style={{ fontSize: 13, color: UI.slate }}>{item.title}: {item.sync_error || 'Unknown error'}</div>)}
                      <button onClick={runPush} disabled={pushing} style={{ ...btnBase, marginTop: 8, background: UI.primary, color: '#fff' }}>Retry</button>
                    </div>
                  )}
                </div>
              )}

              {items.length === 0 ? (
                <EmptyState title="Chưa có action items" description="Bạn có thể thêm task thủ công cho meeting này." />
              ) : (
                tree.map((node) => (
                  <ActionItemCard
                    key={node.id}
                    node={node}
                    depth={0}
                    collapsed={collapsed}
                    onToggleCollapse={(id) => setCollapsed((prev) => {
                      const next = new Set(prev)
                      if (next.has(id)) next.delete(id)
                      else next.add(id)
                      return next
                    })}
                    onToggleSelected={toggleSelected}
                    onEdit={openEdit}
                    onApprove={handleApprove}
                    onReject={handleReject}
                  />
                ))
              )}
            </div>
          )}
        </>
      )}

      {editDraft && (
        <Modal onClose={() => setEditDraft(null)}>
          <h3 style={{ marginTop: 0 }}>Edit action item</h3>
          <ActionItemForm draft={editDraft} onChange={setEditDraft} />
          <ModalActions saving={saving} onCancel={() => setEditDraft(null)} onSave={saveEdit} />
        </Modal>
      )}

      {addDraft && (
        <Modal onClose={() => setAddDraft(null)}>
          <h3 style={{ marginTop: 0 }}>Add task</h3>
          <div style={{ marginBottom: 10 }}>
            <label style={{ display: 'block', marginBottom: 6, fontWeight: 600 }}>Parent epic</label>
            <select value={addDraft.parent_id ?? ''} onChange={(e) => setAddDraft({ ...addDraft, parent_id: e.target.value || null })} style={inputStyle}>
              <option value="">No parent</option>
              {epics.map((epic) => <option key={epic.id} value={epic.id}>{epic.title}</option>)}
            </select>
          </div>
          <ActionItemForm draft={addDraft} onChange={setAddDraft} />
          <ModalActions saving={saving} onCancel={() => setAddDraft(null)} onSave={saveAdd} />
        </Modal>
      )}
    </div>
  )
}

function ActionItemForm<T extends EditDraft | AddDraft>({ draft, onChange }: { draft: T; onChange: (draft: T) => void }) {
  return (
    <div style={{ display: 'grid', gap: 10 }}>
      <input value={draft.title} onChange={(e) => onChange({ ...draft, title: e.target.value })} placeholder="Title" style={inputStyle} />
      <textarea value={draft.description} onChange={(e) => onChange({ ...draft, description: e.target.value })} placeholder="Description" rows={3} style={{ ...inputStyle, resize: 'vertical' }} />
      <textarea value={draft.context} onChange={(e) => onChange({ ...draft, context: e.target.value })} placeholder="Context" rows={3} style={{ ...inputStyle, resize: 'vertical' }} />
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
        <input value={draft.assignee} onChange={(e) => onChange({ ...draft, assignee: e.target.value })} placeholder="Assignee" style={inputStyle} />
        <input value={draft.deadline} onChange={(e) => onChange({ ...draft, deadline: e.target.value })} placeholder="YYYY-MM-DD" style={inputStyle} />
        <select value={draft.priority} onChange={(e) => onChange({ ...draft, priority: e.target.value as ActionItemPriority })} style={inputStyle}>
          {(['critical', 'high', 'medium', 'low'] as ActionItemPriority[]).map((priority) => <option key={priority} value={priority}>{priority}</option>)}
        </select>
      </div>
    </div>
  )
}

function ModalActions({ saving, onCancel, onSave }: { saving: boolean; onCancel: () => void; onSave: () => void }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 16 }}>
      <button onClick={onCancel} style={{ ...btnBase, background: UI.canvas, color: UI.ink, border: `1px solid ${UI.hairlineStrong}` }}>Cancel</button>
      <button onClick={onSave} disabled={saving} style={{ ...btnBase, background: saving ? UI.hairline : UI.primary, color: '#fff' }}>{saving ? 'Saving...' : 'Save'}</button>
    </div>
  )
}
