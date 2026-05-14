import { useAppStore } from '../store/appStore'
import { useQuery } from '@tanstack/react-query'
import { getAnalysisResult } from '../api/supabase/analysis.api'
import { buildActionItemTree, ActionItemTreeNode } from '../hooks/supabase/actionItemTree'
import type { ActionItem } from '../types/supabase-models'

interface Props {
  onNavigate?: (route: string) => void
}

type PriorityGroup = 'high' | 'medium' | 'low'

interface NoteAction {
  id: string
  title: string
  description: string
  assignee: string | null
  deadline: string | null
  priority: string
  context: string
  confidence: number
  topic?: string
  subtasks: ActionItem[]
}

const UI = {
  ink: '#0f172a',
  text: '#1e293b',
  muted: '#64748b',
  hairline: '#e2e8f0',
  paper: '#ffffff',
  high: '#dc2626',
  medium: '#f97316',
  low: '#d97706',
  accent: '#2563eb',
}

function parseJsonbArray(val: unknown): string[] {
  if (!val) return []
  if (Array.isArray(val)) return val.filter((item): item is string => typeof item === 'string')
  if (typeof val === 'string') {
    try {
      const parsed = JSON.parse(val) as unknown
      return parseJsonbArray(parsed)
    } catch {
      return []
    }
  }
  return []
}

function getRawArray(raw: Record<string, unknown> | undefined, key: string): string[] {
  return parseJsonbArray(raw?.[key])
}

function paragraphLines(text: string | null | undefined): string[] {
  if (!text) return []
  return text
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
}

function priorityGroup(priority: string): PriorityGroup {
  const normalized = priority.toLowerCase()
  if (normalized === 'critical' || normalized === 'high') return 'high'
  if (normalized === 'medium') return 'medium'
  return 'low'
}

function priorityLabel(group: PriorityGroup): string {
  if (group === 'high') return 'HIGH'
  if (group === 'medium') return 'MEDIUM'
  return 'LOW'
}

function priorityColor(group: PriorityGroup): string {
  if (group === 'high') return UI.high
  if (group === 'medium') return UI.medium
  return UI.low
}

function formatAssignee(assignee: string | null): string {
  return assignee ? `[@${assignee}]` : ''
}

function formatDue(deadline: string | null): string {
  if (!deadline) return ''
  try {
    return new Date(deadline).toLocaleDateString('vi-VN')
  } catch {
    return deadline
  }
}

function collectActions(nodes: ActionItemTreeNode[], inheritedTopic?: string): NoteAction[] {
  const actions: NoteAction[] = []

  for (const node of nodes) {
    const item = node.item
    const topic = item.item_type === 'epic' ? item.title : inheritedTopic

    if (item.item_type === 'task') {
      actions.push({
        id: item.id,
        title: item.title,
        description: item.description,
        assignee: item.assignee,
        deadline: item.deadline,
        priority: item.priority,
        context: item.context,
        confidence: item.confidence_score,
        topic,
        subtasks: node.children.map((child) => child.item).filter((child) => child.item_type === 'subtask'),
      })
      continue
    }

    if (item.item_type === 'subtask') {
      actions.push({
        id: item.id,
        title: item.title,
        description: item.description,
        assignee: item.assignee,
        deadline: item.deadline,
        priority: item.priority,
        context: item.context,
        confidence: item.confidence_score,
        topic,
        subtasks: [],
      })
      continue
    }

    actions.push(...collectActions(node.children, topic))
  }

  return actions
}

function groupActions(actions: NoteAction[]): Record<PriorityGroup, NoteAction[]> {
  return actions.reduce<Record<PriorityGroup, NoteAction[]>>(
    (acc, action) => {
      acc[priorityGroup(action.priority)].push(action)
      return acc
    },
    { high: [], medium: [], low: [] }
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h3 style={{ fontSize: 16, lineHeight: 1.35, fontWeight: 800, color: UI.ink, margin: '24px 0 8px' }}>
      {children}
    </h3>
  )
}

function BulletList({ items }: { items: string[] }) {
  if (items.length === 0) return null
  return (
    <ul style={{ margin: 0, paddingLeft: 22, display: 'flex', flexDirection: 'column', gap: 5 }}>
      {items.map((item, idx) => (
        <li key={`${item}-${idx}`} style={{ fontSize: 14, lineHeight: 1.55, color: UI.text }}>
          {item}
        </li>
      ))}
    </ul>
  )
}

function ActionGroup({
  group,
  items,
  startIndex,
}: {
  group: PriorityGroup
  items: NoteAction[]
  startIndex: number
}) {
  if (items.length === 0) return null

  return (
    <div style={{ marginTop: 20 }}>
      <div style={{ color: priorityColor(group), fontSize: 16, lineHeight: 1.35, fontWeight: 800, marginBottom: 8 }}>
        {priorityLabel(group)}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {items.map((action, idx) => {
          const due = formatDue(action.deadline)
          const assignee = formatAssignee(action.assignee)
          return (
            <div key={action.id}>
              <div style={{ fontSize: 15, lineHeight: 1.5, color: UI.ink, fontWeight: 650 }}>
                {startIndex + idx}. {action.title}
                {assignee && <span style={{ color: '#16a34a', fontWeight: 600 }}> {assignee}</span>}
              </div>
              {action.topic && (
                <div style={{ color: UI.muted, fontSize: 12, marginTop: 2 }}>
                  Topic: {action.topic}
                </div>
              )}
              <ul style={{ margin: '7px 0 0', paddingLeft: 24, display: 'flex', flexDirection: 'column', gap: 4 }}>
                {action.description && (
                  <li style={{ fontSize: 14, lineHeight: 1.55, color: UI.text }}>
                    <strong>Action:</strong> {action.description}
                  </li>
                )}
                {due && (
                  <li style={{ fontSize: 14, lineHeight: 1.55, color: UI.text }}>
                    <strong>Due:</strong> {due}
                  </li>
                )}
                {action.context && action.context !== action.description && (
                  <li style={{ fontSize: 14, lineHeight: 1.55, color: UI.text }}>
                    <strong>Context:</strong> {action.context}
                  </li>
                )}
                {action.subtasks.map((subtask) => (
                  <li key={subtask.id} style={{ fontSize: 14, lineHeight: 1.55, color: UI.text }}>
                    <strong>Subtask:</strong> {subtask.title}
                    {subtask.assignee && <span style={{ color: '#16a34a' }}> {formatAssignee(subtask.assignee)}</span>}
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function ResultsView({ onNavigate }: Props) {
  const { currentMeetingTitle, currentMeetingId } = useAppStore()
  const canReview = !!onNavigate && !!currentMeetingId

  const { data, isLoading, error } = useQuery({
    queryKey: ['analysisResult', currentMeetingId],
    queryFn: () => getAnalysisResult(currentMeetingId!),
    enabled: !!currentMeetingId,
  })

  const analysisRaw = data?.analysis_result
  const trees = data?.action_items ? buildActionItemTree(data.action_items) : []
  const rawResponse = analysisRaw?.raw_response
  const summaryLines = paragraphLines(analysisRaw?.summary_text)
  const keyDecisions = parseJsonbArray(analysisRaw?.key_decisions)
  const parkingLot = parseJsonbArray(analysisRaw?.parking_lot)
  const discussionPoints = [
    ...getRawArray(rawResponse, 'discussion_points'),
    ...getRawArray(rawResponse, 'insights'),
  ]
  const groupedActions = groupActions(collectActions(trees))
  const highCount = groupedActions.high.length
  const mediumStart = highCount + 1
  const lowStart = highCount + groupedActions.medium.length + 1
  const hasActions = highCount + groupedActions.medium.length + groupedActions.low.length > 0

  return (
    <div style={{ maxWidth: 980, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 18, gap: 16, flexWrap: 'wrap' }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 750, color: UI.ink, margin: '0 0 4px' }}>
            {currentMeetingTitle || 'Meeting note'}
          </h2>
          <p style={{ fontSize: 12, color: UI.muted, margin: 0 }}>
            Meeting note được tạo từ transcript và action items.
          </p>
        </div>
        {canReview && (
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            <button
              onClick={() => onNavigate!('review_transcript')}
              style={{
                padding: '9px 16px',
                background: '#fff',
                color: UI.ink,
                border: `1px solid ${UI.hairline}`,
                borderRadius: 8,
                fontWeight: 700,
                fontSize: 13,
                cursor: 'pointer',
              }}
            >
              Transcript
            </button>
            <button
              onClick={() => onNavigate!('review')}
              style={{
                padding: '9px 16px',
                background: UI.accent,
                color: '#fff',
                border: 'none',
                borderRadius: 8,
                fontWeight: 700,
                fontSize: 13,
                cursor: 'pointer',
              }}
            >
              Review &amp; Push Jira
            </button>
          </div>
        )}
      </div>

      {isLoading ? (
        <div style={{ background: UI.paper, borderRadius: 8, border: `1px solid ${UI.hairline}`, padding: 24, textAlign: 'center', color: UI.muted }}>
          Đang tải kết quả phân tích từ cơ sở dữ liệu...
        </div>
      ) : error ? (
        <div style={{ background: '#fef2f2', borderRadius: 8, border: '1px solid #fecaca', padding: 24, color: '#ef4444' }}>
          Đã có lỗi xảy ra: {error instanceof Error ? error.message : String(error)}
        </div>
      ) : !analysisRaw ? (
        <div style={{ background: UI.paper, borderRadius: 8, border: `1px solid ${UI.hairline}`, padding: 24, color: '#94a3b8' }}>
          Chưa có kết quả phân tích. Phân tích đang chạy hoặc bạn chưa khởi tạo nội dung cho meeting này.
        </div>
      ) : (
        <article
          style={{
            background: UI.paper,
            border: `1px solid ${UI.hairline}`,
            borderRadius: 8,
            padding: '26px 34px 34px',
            color: UI.text,
            boxShadow: '0 1px 2px rgba(15, 23, 42, 0.04)',
          }}
        >
          <h1 style={{ fontSize: 23, lineHeight: 1.25, color: UI.ink, margin: '0 0 22px', fontWeight: 800 }}>
            Meeting note
          </h1>

          <SectionTitle>Insight</SectionTitle>
          {summaryLines.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
              {summaryLines.map((line, idx) => (
                <p key={`${line}-${idx}`} style={{ fontSize: 14, lineHeight: 1.65, color: UI.text, margin: 0 }}>
                  {line}
                </p>
              ))}
            </div>
          ) : (
            <p style={{ fontSize: 15, color: UI.muted, margin: 0 }}>Không có tóm tắt.</p>
          )}

          {discussionPoints.length > 0 && (
            <>
              <SectionTitle>Discussion points</SectionTitle>
              <BulletList items={discussionPoints} />
            </>
          )}

          {keyDecisions.length > 0 && (
            <>
              <SectionTitle>Key decisions</SectionTitle>
              <BulletList items={keyDecisions} />
            </>
          )}

          <SectionTitle>Action plan</SectionTitle>
          {hasActions ? (
            <>
              <ActionGroup group="high" items={groupedActions.high} startIndex={1} />
              <ActionGroup group="medium" items={groupedActions.medium} startIndex={mediumStart} />
              <ActionGroup group="low" items={groupedActions.low} startIndex={lowStart} />
            </>
          ) : (
            <p style={{ fontSize: 15, color: UI.muted, margin: 0 }}>
              Chưa có action items nào cho meeting này.
            </p>
          )}

          {parkingLot.length > 0 && (
            <>
              <SectionTitle>Parking lot</SectionTitle>
              <BulletList items={parkingLot} />
            </>
          )}
        </article>
      )}
    </div>
  )
}
