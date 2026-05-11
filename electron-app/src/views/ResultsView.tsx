import { useAppStore } from '../store/appStore'
import ConfidenceBadge from '../components/ConfidenceBadge'
import type { Epic, Task } from '../types/schema'

interface Props {
  onNavigate?: (route: string) => void
}

function TaskCard({ task, epicIdx, taskIdx }: { task: Task; epicIdx: number; taskIdx: number }) {
  return (
    <div
      style={{
        padding: 12, background: '#f8fafc', borderRadius: 12, border: '1px solid #f1f5f9',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 6 }}>
        <div style={{ fontWeight: 700, fontSize: 13, flex: 1, color: '#0f172a' }}>
          Task {epicIdx}.{taskIdx}: {task.summary}
        </div>
        {task.confidence > 0 && <ConfidenceBadge confidence={task.confidence} />}
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

function EpicCard({ epic, idx }: { epic: Epic; idx: number }) {
  return (
    <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #e2e8f0', padding: 20, marginBottom: 12 }}>
      <div style={{ fontWeight: 800, fontSize: 16, color: '#0f172a', marginBottom: 6 }}>
        Epic {idx}: {epic.summary}
      </div>
      {epic.description && (
        <div style={{ fontSize: 13, color: '#64748b', marginBottom: 12 }}>{epic.description}</div>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {epic.tasks.map((task, j) => (
          <TaskCard key={j} task={task} epicIdx={idx} taskIdx={j + 1} />
        ))}
      </div>
    </div>
  )
}

export default function ResultsView({ onNavigate }: Props) {
  const { selectedMeeting, analysis, currentMeetingId } = useAppStore()

  const canReview = !!onNavigate && !!currentMeetingId

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: '#0f172a', marginBottom: 4 }}>
            {selectedMeeting?.title || 'Results'}
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

      {!analysis ? (
        <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #e2e8f0', padding: 24, color: '#94a3b8' }}>
          Chưa có kết quả phân tích. Hãy chạy Analyze trong New Meeting trước.
        </div>
      ) : (
        <>
          {/* Summary card */}
          {analysis.summary && (
            <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #e2e8f0', padding: 20, marginBottom: 12 }}>
              <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 8, color: '#0f172a' }}>📝 Tóm tắt</div>
              <p style={{ fontSize: 13, color: '#334155', lineHeight: 1.6 }}>{analysis.summary}</p>
            </div>
          )}

          {/* Key decisions */}
          {analysis.key_decisions?.length > 0 && (
            <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #e2e8f0', padding: 20, marginBottom: 12 }}>
              <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 8, color: '#0f172a' }}>✅ Quyết định chính</div>
              <ul style={{ paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 4 }}>
                {analysis.key_decisions.map((d, i) => (
                  <li key={i} style={{ fontSize: 13, color: '#334155' }}>{d}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Epics */}
          {analysis.epics.map((epic, i) => (
            <EpicCard key={i} epic={epic} idx={i + 1} />
          ))}
        </>
      )}
    </div>
  )
}
