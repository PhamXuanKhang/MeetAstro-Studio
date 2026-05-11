import { useAppStore } from '../store/appStore'
import { useQuery } from '@tanstack/react-query'
import { getAnalysisResult } from '../api/supabase/analysis.api'
import { buildActionItemTree, ActionItemTreeNode } from '../hooks/supabase/actionItemTree'
import ConfidenceBadge from '../components/ConfidenceBadge'

interface Props {
  onNavigate?: (route: string) => void
}

function TaskNodeCard({ node, epicIdx, taskIdx }: { node: ActionItemTreeNode; epicIdx: number; taskIdx: number }) {
  const task = node.item
  return (
    <div style={{ padding: 12, background: '#f8fafc', borderRadius: 12, border: '1px solid #f1f5f9' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 6 }}>
        <div style={{ fontWeight: 700, fontSize: 13, flex: 1, color: '#0f172a' }}>
          Task {epicIdx}.{taskIdx}: {task.title}
        </div>
        {(task.confidence_score ?? 0) > 0 && <ConfidenceBadge confidence={task.confidence_score!} />}
      </div>
      <div style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>
        👤 {task.assignee || 'TBD'} &nbsp;|&nbsp; 📅 {task.deadline || 'N/A'} &nbsp;|&nbsp; 🔥 {task.priority}
      </div>
      {task.context && (
        <div style={{ fontSize: 11, color: '#94a3b8', fontStyle: 'italic' }}>{task.context}</div>
      )}
    </div>
  )
}

function EpicNodeCard({ node, idx }: { node: ActionItemTreeNode; idx: number }) {
  const epic = node.item
  return (
    <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #e2e8f0', padding: 20, marginBottom: 12 }}>
      <div style={{ fontWeight: 800, fontSize: 16, color: '#0f172a', marginBottom: 6 }}>
        Epic {idx}: {epic.title}
      </div>
      {epic.description && (
        <div style={{ fontSize: 13, color: '#64748b', marginBottom: 12 }}>{epic.description}</div>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {node.children.map((taskNode, j) => (
          <TaskNodeCard key={taskNode.item.id} node={taskNode} epicIdx={idx} taskIdx={j + 1} />
        ))}
      </div>
    </div>
  )
}

export default function ResultsView({ onNavigate }: Props) {
  // Bỏ analysis cũ, chỉ lấy id meeting hiện tại
  const { currentMeetingTitle, currentMeetingId } = useAppStore()
  const canReview = !!onNavigate && !!currentMeetingId

  // Dùng React Query fetch data từ Supabase SDK
  const { data, isLoading, error } = useQuery({
    queryKey: ['analysisResult', currentMeetingId],
    queryFn: () => getAnalysisResult(currentMeetingId!),
    enabled: !!currentMeetingId,
  })

  const analysisRaw = data?.analysis_result
  // Biến mảng phẳng action_items thành cây cha/con để in ra Epics (Nếu bạn có bơm data này vào)
  const trees = data?.action_items ? buildActionItemTree(data.action_items) : []

  // Helper bóc JSONB mảng an toàn (đề phòng db trả về chuỗi JSON string thay vì object array thật)
  const parseJsonbArray = (val: unknown): string[] => {
    if (!val) return []
    if (Array.isArray(val)) return val as string[]
    if (typeof val === 'string') {
      try { return JSON.parse(val) as string[] } catch { return [] }
    }
    return []
  }

  const keyDecisions = parseJsonbArray(analysisRaw?.key_decisions)
  const parkingLot = parseJsonbArray(analysisRaw?.parking_lot)

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: '#0f172a', marginBottom: 4 }}>
            {currentMeetingTitle || 'Results'}
          </h2>
          <p style={{ fontSize: 12, color: '#64748b' }}>
            Review extracted epics, tasks, and subtasks before pushing to Jira.
          </p>
        </div>
        {canReview && (
          <button
            onClick={() => onNavigate!('review')}
            style={{
              padding: '10px 20px', background: '#2563eb', color: '#fff', border: 'none',
              borderRadius: 10, fontWeight: 700, fontSize: 14, cursor: 'pointer',
            }}
          >
            📋 Review &amp; Push to Jira
          </button>
        )}
      </div>

      {isLoading ? (
        <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #e2e8f0', padding: 24, alignContent: 'center', textAlign: 'center', color: '#64748b' }}>
          Đang tải kết quả phân tích từ cơ sở dữ liệu...
        </div>
      ) : error ? (
        <div style={{ background: '#fef2f2', borderRadius: 16, border: '1px solid #fecaca', padding: 24, color: '#ef4444' }}>
          Đã có lỗi xảy ra: {error instanceof Error ? error.message : String(error)}
        </div>
      ) : !analysisRaw ? (
        <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #e2e8f0', padding: 24, color: '#94a3b8' }}>
          Chưa có kết quả phân tích. Phân tích đang chạy hoặc bạn chưa khởi tạo nội dung cho meeting này.
        </div>
      ) : (
        <>
          {/* Summary card */}
            <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #e2e8f0', padding: 20, marginBottom: 12 }}>
              <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 8, color: '#0f172a' }}>📝 Tóm tắt</div>
              <p style={{ fontSize: 13, color: '#334155', lineHeight: 1.6 }}>{analysisRaw.summary_text ?? "Không có tóm tắt"}</p>
            </div>

          {/* Key decisions */}
          {keyDecisions.length > 0 && (
            <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #e2e8f0', padding: 20, marginBottom: 12 }}>
              <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 8, color: '#0f172a' }}>✅ Quyết định chính</div>
              <ul style={{ paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 4 }}>
                {keyDecisions.map((d, i) => (
                  <li key={i} style={{ fontSize: 13, color: '#334155' }}>{d}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Parking lot */}
          {parkingLot.length > 0 && (
            <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #e2e8f0', padding: 20, marginBottom: 12 }}>
              <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 8, color: '#0f172a' }}>🚧 Parking Lot (Chưa chốt)</div>
              <ul style={{ paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 4 }}>
                {parkingLot.map((p, i) => (
                  <li key={i} style={{ fontSize: 13, color: '#334155' }}>{p}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Epics (Đã tự động đệ quy Action Items qua actionItemTree hooks) */}
          {trees.length > 0 ? (
            trees.map((epicNode, i) => (
              <EpicNodeCard key={epicNode.item.id} node={epicNode} idx={i + 1} />
            ))
          ) : (
            <div style={{ background: '#fff', borderRadius: 16, border: '1px dotted #e2e8f0', padding: 20, color: '#64748b', fontSize: 13 }}>
              Cơ sở dữ liệu chưa có Action Items nào cho meeting này.
            </div>
          )}
        </>
      )}
    </div>
  )
}
