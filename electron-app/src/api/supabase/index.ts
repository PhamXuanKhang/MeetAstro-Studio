/**
 * Supabase SDK Data Access Layer – Barrel Export
 *
 * Import all Supabase SDK functions from this single entry point:
 *   import { createMeeting, getTranscriptSegments, ... } from '../api/supabase';
 */

// Types (re-export for consumer convenience)
export type {
  Meeting,
  TranscriptSegment,
  AnalysisResult,
  ActionItem,
  MeetingStatus,
  ActionItemType,
  ActionItemPriority,
  ActionItemReviewStatus,
  SyncStatus,
  CreateMeetingPayload,
  RenameSpeakerPayload,
  EditTranscriptPayload,
  EditActionItemPayload,
  ApproveActionItemPayload,
  RejectActionItemPayload,
  AddManualActionItemPayload,
  ListMeetingsParams,
  MeetingsListResult,
  MeetingDetailResult,
  AnalysisWithItemsResult,
  ConfidenceScoreItem,
  JiraIssueLink,
} from '../../types/supabase-models';

// Meetings (C1, C9, H1, H4, H5)
export {
  createMeeting,
  getMeetingPipelineStatus,
  listMeetings,
  getMeetingDetail,
  deleteMeeting,
} from './meetings.api';

// Transcript (D2, D3, D4, D5)
export {
  getTranscriptSegments,
  getDiarization,
  renameSpeaker,
  editTranscriptSegment,
} from './transcript.api';

// Analysis (E2, E3, E6)
export {
  getMeetingSummary,
  getAnalysisResult,
  getConfidenceScores,
} from './analysis.api';

// Action Items (F1, F5, F6, F8 + list + bulk)
export {
  listActionItems,
  bulkApproveActionItems,
  editActionItem,
  approveActionItem,
  rejectActionItem,
  addManualActionItem,
} from './actionItem.api';

// Jira Sync (G4)
export { getJiraIssueLinks } from './jiraSync.api';

// Realtime (C9, D1, G2)
export {
  subscribeMeetingStatus,
  subscribeTranscriptSegments,
  subscribeActionItemSyncStatus,
  unsubscribeChannel,
} from './realtime';
