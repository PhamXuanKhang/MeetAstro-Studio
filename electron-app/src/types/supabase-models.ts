/**
 * Supabase Data Models
 * ---
 * Derived from "Shared Shapes" in docs/backend-contract-v1.md.
 * These types mirror Supabase DB tables and are used exclusively
 * by the Supabase SDK data-access layer (src/api/supabase/).
 */

// ─── Enums ───────────────────────────────────────────────

export type MeetingStatus =
  | 'pending'
  | 'transcribing'
  | 'transcribed'
  | 'analyzing'
  | 'draft'
  | 'approved'
  | 'pushed'
  | 'failed';

export type StorageProvider = 'local';

export type ActionItemType = 'epic' | 'task' | 'subtask';

export type ActionItemPriority = 'critical' | 'high' | 'medium' | 'low';

export type ActionItemReviewStatus = 'draft' | 'edited' | 'approved' | 'rejected';

export type SyncStatus = 'pending' | 'syncing' | 'synced' | 'failed';

// ─── Domain Models (Table Rows) ─────────────────────────

/** Mirrors `meetings` table in Supabase. */
export interface Meeting {
  id: string;
  user_id: string;
  title: string;
  status: MeetingStatus;
  storage_provider: StorageProvider;
  audio_storage_path: string | null;
  audio_duration_seconds: number | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

/** Mirrors `transcript_segments` table in Supabase. */
export interface TranscriptSegment {
  id: string;
  meeting_id: string;
  speaker: string;
  start_time: number;
  end_time: number;
  content: string;
}

/** Mirrors `analysis_results` table in Supabase. */
export interface AnalysisResult {
  id: string;
  meeting_id: string;
  summary_text: string;
  key_decisions: string[];
  parking_lot: string[];
  raw_response: Record<string, unknown>;
  ai_model: string;
  input_tokens: number;
  output_tokens: number;
  created_at: string;
}

/** Mirrors `action_items` table in Supabase. */
export interface ActionItem {
  id: string;
  meeting_id: string;
  parent_id: string | null;
  item_type: ActionItemType;
  title: string;
  description: string;
  assignee: string | null;
  deadline: string | null;
  priority: ActionItemPriority;
  context: string;
  confidence_score: number;
  review_status: ActionItemReviewStatus;
  is_selected: boolean;
  sync_status: SyncStatus;
  sync_error: string | null;
  jira_issue_key: string | null;
  jira_issue_url: string | null;
  created_at: string;
  updated_at: string;
}

// ─── Request DTOs ────────────────────────────────────────

/** C1 – Create Meeting */
export interface CreateMeetingPayload {
  title: string;
  status?: MeetingStatus;
  storage_provider?: StorageProvider;
  audio_storage_path?: string | null;
  audio_duration_seconds?: number | null;
}

/** D4 – Rename Speaker */
export interface RenameSpeakerPayload {
  meeting_id: string;
  from_speaker: string;
  to_speaker: string;
}

/** D5 – Edit Transcript Text */
export interface EditTranscriptPayload {
  segment_id: string;
  content: string;
}

/** F1 – Edit Action Item */
export interface EditActionItemPayload {
  action_item_id: string;
  title?: string;
  description?: string;
  context?: string;
  assignee?: string | null;
  deadline?: string | null;
  priority?: ActionItemPriority;
  review_status?: ActionItemReviewStatus;
  is_selected?: boolean;
}

/** F5 – Approve Action Item */
export interface ApproveActionItemPayload {
  action_item_id: string;
  review_status: 'approved';
  is_selected: true;
}

/** F6 – Reject Action Item */
export interface RejectActionItemPayload {
  action_item_id: string;
  review_status: 'rejected';
  is_selected: false;
}

/** F8 – Add Manual Action Item */
export interface AddManualActionItemPayload {
  meeting_id: string;
  parent_id?: string | null;
  item_type: ActionItemType;
  title: string;
  description?: string;
  assignee?: string | null;
  deadline?: string | null;
  priority?: ActionItemPriority;
  context?: string;
  confidence_score?: number;
  review_status?: ActionItemReviewStatus;
  is_selected?: boolean;
  sync_status?: SyncStatus;
}

/** H1 – View Meetings History */
export interface ListMeetingsParams {
  limit?: number;
  offset?: number;
}

// ─── Response DTOs ───────────────────────────────────────

/** H1 – Meeting list response */
export type MeetingListItem = Pick<
  Meeting,
  'id' | 'title' | 'status' | 'audio_duration_seconds' | 'created_at' | 'updated_at'
> & {
  jira_links_count?: number;
};

export interface MeetingsListResult {
  items: MeetingListItem[];
  total: number;
}

/** H4 – Old Meeting Detail */
export interface MeetingDetailResult {
  meeting: Meeting;
  analysis_result: AnalysisResult | null;
  transcript_segments: TranscriptSegment[];
  action_items: ActionItem[];
}

/** E3 – Analysis + action items */
export interface AnalysisWithItemsResult {
  analysis_result: Pick<AnalysisResult, 'summary_text' | 'key_decisions' | 'parking_lot' | 'raw_response'> | null;
  action_items: ActionItem[];
}

/** E6 – Confidence scores */
export interface ConfidenceScoreItem {
  id: string;
  title: string;
  confidence_score: number;
}

/** G4 – Jira issue links */
export interface JiraIssueLink {
  id: string;
  jira_issue_key: string;
  jira_issue_url: string;
}
