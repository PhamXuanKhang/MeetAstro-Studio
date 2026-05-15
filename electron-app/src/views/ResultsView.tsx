import { useAppStore } from '../store/appStore'
import { useQuery } from '@tanstack/react-query'
import { getAnalysisResult } from '../api/supabase/analysis.api'
import { buildActionItemTree, ActionItemTreeNode } from '../hooks/supabase/actionItemTree'
import type { ActionItem } from '../types/supabase-models'
import { Badge, Button, Card, EmptyState, Icon } from '../components/ui'

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

function priorityVariant(group: PriorityGroup): 'error' | 'warning' | 'default' {
  if (group === 'high') return 'error'
  if (group === 'medium') return 'warning'
  return 'default'
}

function priorityColor(group: PriorityGroup): string {
  if (group === 'high') return 'var(--color-danger)'
  if (group === 'medium') return 'var(--color-warning)'
  return 'var(--color-text-muted)'
}

function formatAssignee(assignee: string | null): string {
  return assignee ? `@${assignee}` : ''
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

function SectionTitle({ icon, children }: { icon: string; children: React.ReactNode }) {
  return (
    <h3 style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 16, lineHeight: 1.35, fontWeight: 800, color: 'var(--color-text-main)', margin: '24px 0 10px' }}>
      <Icon name={icon} size={18} style={{ color: 'var(--color-primary)' }} />
      {children}
    </h3>
  )
}

function BulletList({ items }: { items: string[] }) {
  if (items.length === 0) return null
  return (
    <ul style={{ margin: 0, paddingLeft: 22, display: 'flex', flexDirection: 'column', gap: 6 }}>
      {items.map((item, idx) => (
        <li key={`${item}-${idx}`} style={{ fontSize: 14, lineHeight: 1.6, color: 'var(--color-text-main)' }}>
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
    <div style={{ marginTop: 18 }}>
      <Badge variant={priorityVariant(group)}>{priorityLabel(group)}</Badge>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginTop: 12 }}>
        {items.map((action, idx) => {
          const due = formatDue(action.deadline)
          const assignee = formatAssignee(action.assignee)
          return (
            <Card key={action.id} style={{ padding: 16, boxShadow: 'none' }}>
              <div style={{ fontSize: 15, lineHeight: 1.5, color: 'var(--color-text-main)', fontWeight: 800 }}>
                <span style={{ color: priorityColor(group) }}>{startIndex + idx}.</span> {action.title}
                {assignee && <span style={{ color: 'var(--color-success)', fontWeight: 700 }}> [{assignee}]</span>}
              </div>
              {action.topic && (
                <div style={{ color: 'var(--color-text-muted)', fontSize: 12, marginTop: 4 }}>
                  Topic: {action.topic}
                </div>
              )}
              <ul style={{ margin: '9px 0 0', paddingLeft: 22, display: 'flex', flexDirection: 'column', gap: 5 }}>
                {action.description && (
                  <li style={{ fontSize: 14, lineHeight: 1.55, color: 'var(--color-text-main)' }}>
                    <strong>Action:</strong> {action.description}
                  </li>
                )}
                {due && (
                  <li style={{ fontSize: 14, lineHeight: 1.55, color: 'var(--color-text-main)' }}>
                    <strong>Due:</strong> {due}
                  </li>
                )}
                {action.context && action.context !== action.description && (
                  <li style={{ fontSize: 14, lineHeight: 1.55, color: 'var(--color-text-main)' }}>
                    <strong>Context:</strong> {action.context}
                  </li>
                )}
                {action.subtasks.map((subtask) => (
                  <li key={subtask.id} style={{ fontSize: 14, lineHeight: 1.55, color: 'var(--color-text-main)' }}>
                    <strong>Subtask:</strong> {subtask.title}
                    {subtask.assignee && <span style={{ color: 'var(--color-success)' }}> [{formatAssignee(subtask.assignee)}]</span>}
                  </li>
                ))}
              </ul>
            </Card>
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
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <Icon name="summarize" size={22} style={{ color: 'var(--color-primary)' }} />
            <h2 style={{ fontSize: 22, fontWeight: 800, color: 'var(--color-text-main)', margin: 0 }}>
              {currentMeetingTitle || 'Meeting note'}
            </h2>
          </div>
          <p style={{ fontSize: 13, color: 'var(--color-text-muted)', margin: 0 }}>
            Meeting note được tạo từ transcript và action items.
          </p>
        </div>
        {canReview && (
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            <Button variant="outline" onClick={() => onNavigate!('review_transcript')}><Icon name="article" size={16} /> Transcript</Button>
            <Button variant="primary" onClick={() => onNavigate!('review')}><Icon name="rule" size={16} /> Review &amp; Push Jira</Button>
          </div>
        )}
      </div>

      {isLoading ? (
        <Card style={{ padding: 24, textAlign: 'center', color: 'var(--color-text-muted)' }}>
          <Icon name="progress_activity" size={24} style={{ color: 'var(--color-primary)', animation: 'spin 0.8s linear infinite', marginBottom: 8 }} />
          <div>Đang tải kết quả phân tích từ cơ sở dữ liệu...</div>
        </Card>
      ) : error ? (
        <Card style={{ padding: 24, background: 'color-mix(in srgb, var(--color-danger) 10%, var(--color-surface))', color: 'var(--color-danger)' }}>
          Đã có lỗi xảy ra: {error instanceof Error ? error.message : String(error)}
        </Card>
      ) : !analysisRaw ? (
        <Card><EmptyState icon="draft" title="Chưa có kết quả phân tích" description="Phân tích đang chạy hoặc bạn chưa khởi tạo nội dung cho meeting này." /></Card>
      ) : (
        <article>
          <Card style={{ padding: '28px 34px 34px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
              <Icon name="notes" size={24} style={{ color: 'var(--color-primary)' }} />
              <h1 style={{ fontSize: 24, lineHeight: 1.25, color: 'var(--color-text-main)', margin: 0, fontWeight: 900 }}>
                Meeting note
              </h1>
            </div>

            <SectionTitle icon="lightbulb">Insight</SectionTitle>
            {summaryLines.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {summaryLines.map((line, idx) => (
                  <p key={`${line}-${idx}`} style={{ fontSize: 14, lineHeight: 1.65, color: 'var(--color-text-main)', margin: 0 }}>
                    {line}
                  </p>
                ))}
              </div>
            ) : (
              <p style={{ fontSize: 15, color: 'var(--color-text-muted)', margin: 0 }}>Không có tóm tắt.</p>
            )}

            {discussionPoints.length > 0 && (
              <>
                <SectionTitle icon="forum">Discussion points</SectionTitle>
                <BulletList items={discussionPoints} />
              </>
            )}

            {keyDecisions.length > 0 && (
              <>
                <SectionTitle icon="verified">Key decisions</SectionTitle>
                <BulletList items={keyDecisions} />
              </>
            )}

            <SectionTitle icon="account_tree">Action plan</SectionTitle>
            {hasActions ? (
              <>
                <ActionGroup group="high" items={groupedActions.high} startIndex={1} />
                <ActionGroup group="medium" items={groupedActions.medium} startIndex={mediumStart} />
                <ActionGroup group="low" items={groupedActions.low} startIndex={lowStart} />
              </>
            ) : (
              <p style={{ fontSize: 15, color: 'var(--color-text-muted)', margin: 0 }}>
                Chưa có action items nào cho meeting này.
              </p>
            )}

            {parkingLot.length > 0 && (
              <>
                <SectionTitle icon="inventory_2">Parking lot</SectionTitle>
                <BulletList items={parkingLot} />
              </>
            )}
          </Card>
        </article>
      )}
    </div>
  )
}
