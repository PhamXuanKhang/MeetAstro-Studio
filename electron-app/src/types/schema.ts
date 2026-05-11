// TypeScript interfaces mirroring src/schema.py + src/api/schemas/*.py

export type Priority = 'Critical' | 'High' | 'Medium' | 'Low'
export type ReviewStatus = 'draft' | 'approved' | 'rejected' | 'edited'
export type MeetingStatus =
  | 'pending'
  | 'transcribing'
  | 'transcribed'
  | 'analyzing'
  | 'draft'
  | 'approved'
  | 'pushed'
  | 'failed'
export type JobState = 'PENDING' | 'STARTED' | 'PROGRESS' | 'SUCCESS' | 'FAILURE' | 'RETRY'
export type ItemType = 'epic' | 'task' | 'subtask'
export type ProcessingKind = 'transcribing' | 'finalizing_recording' | 'analyzing'

// --- Domain models (mirrors src/schema.py) ---

export interface Subtask {
  summary: string
  assignee?: string | null
  deadline?: string | null
  priority: Priority
  context: string
  confidence: number
  validation_notes: string[]
}

export interface Task extends Omit<Subtask, never> {
  subtasks: Subtask[]
}

export interface Epic {
  summary: string
  description: string
  tasks: Task[]
}

export interface MeetingAnalysis {
  epics: Epic[]
  summary: string
  key_decisions: string[]
  discussion_points: string[]
  parking_lot: string[]
  created_at: string
}

export interface MeetingRecord {
  id?: string | null
  title: string
  transcript: string
  audio_path?: string | null
  analysis?: MeetingAnalysis | null
  created_at: string
  updated_at: string
}

export interface ReviewItem {
  id?: string | null
  meeting_id: string
  parent_id?: string | null
  item_type: ItemType
  summary: string
  assignee?: string | null
  deadline?: string | null
  priority: Priority
  context: string
  confidence_score: number
  is_flagged: boolean
  review_status: ReviewStatus
  sync_status?: string | null
  jira_issue_key?: string | null
  jira_issue_url?: string | null
  created_at?: string
  updated_at?: string
}

// --- API response schemas (mirrors src/api/schemas/*.py) ---

export interface MeetingResponse {
  id: string
  title: string
  audio_path?: string | null
  status: MeetingStatus
  user_id: string
  celery_task_id?: string | null
  error_message?: string | null
  created_at: string
  updated_at: string
}

export interface MeetingListResponse {
  items: MeetingResponse[]
  total: number
  page: number
  page_size: number
}

export interface TranscriptResponse {
  id: string
  meeting_id: string
  raw_text: string
  diarized_text?: string | null
  language: string
  char_count?: number | null
  created_at: string
}

export interface TranscriptSegment {
  id: string
  meeting_id: string
  speaker: string
  start_time: number
  end_time: number
  content: string
}

export interface TranscriptSegmentsResponse {
  segments: TranscriptSegment[]
}

export interface UpdateTranscriptSegmentRequest {
  content?: string
  speaker?: string
}

export interface RenameSpeakerRequest {
  from_speaker: string
  to_speaker: string
}

export interface AnalysisResponse {
  id: string
  meeting_id: string
  analysis_json: MeetingAnalysis
  summary?: string | null
  overall_confidence?: number | null
  validation_metrics?: Record<string, unknown> | null
  created_at: string
}

export interface AudioUploadResponse {
  meeting_id: string
  job_id: string
  audio_storage_path?: string | null
  audio_duration_seconds?: number | null
  status: string
  message?: string
}

export interface StartAnalysisResponse {
  meeting_id?: string
  job_id: string
  status?: string
  state?: JobState
}

export interface ReviewItemResponse {
  id: string
  meeting_id: string
  parent_id?: string | null
  item_type: ItemType
  summary: string
  description?: string | null
  assignee?: string | null
  deadline?: string | null
  priority?: Priority | null
  context?: string | null
  confidence_score: number
  is_flagged: boolean
  review_status: ReviewStatus
  sync_status?: string | null
  jira_issue_key?: string | null
  jira_issue_url?: string | null
  created_at: string
  updated_at: string
}

export interface ReviewSummaryResponse {
  total: number
  approved: number
  rejected: number
  flagged: number
  pending: number
}

export interface JobStatusResponse {
  job_id: string
  state: JobState
  progress_pct?: number | null
  message?: string | null
  result?: unknown
  error?: string | null
}

export interface JiraPushResponse {
  job_id?: string
  is_stub: boolean
  epic_keys: string[]
  task_count: number
  subtask_count: number
  message: string
}

export interface ProviderListResponse {
  providers: string[]
}
