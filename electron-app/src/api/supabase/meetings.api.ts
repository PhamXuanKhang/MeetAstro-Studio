/**
 * Meetings – Supabase SDK Data Access Layer
 * ---
 * Covers use cases: C1, C9, H1, H4, H5
 * Contract: docs/backend-contract-v1.md
 */

import { supabase } from '../../lib/supabase';
import type {
  Meeting,
  CreateMeetingPayload,
  ListMeetingsParams,
  MeetingsListResult,
  MeetingDetailResult,
  TranscriptSegment,
  AnalysisResult,
  ActionItem,
  ApiResult,
} from '../../types/supabase-models';

// ─── Helpers ─────────────────────────────────────────────

function ensureClient() {
  if (!supabase) {
    throw new Error('Supabase client chưa được khởi tạo. Kiểm tra biến môi trường VITE_SUPABASE_URL và VITE_SUPABASE_ANON_KEY.');
  }
  return supabase;
}

// ─── C1 – Create Meeting ────────────────────────────────

/**
 * Tạo một meeting mới với status mặc định "pending".
 * RLS đảm bảo user_id tự gán qua `auth.uid()`.
 */
export async function createMeeting(
  payload: CreateMeetingPayload
): Promise<ApiResult<Meeting>> {
  try {
    const client = ensureClient();
    const { data, error } = await client
      .from('meetings')
      .insert({
        title: payload.title,
        status: payload.status ?? 'pending',
        storage_provider: payload.storage_provider ?? 'local',
        audio_storage_path: payload.audio_storage_path ?? null,
        audio_duration_seconds: payload.audio_duration_seconds ?? null,
      })
      .select()
      .single();

    if (error) throw error;
    return { data: data as Meeting, error: null };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`[C1] Tạo meeting thất bại: ${message}`);
  }
}

// ─── C9 – View Pipeline Status ──────────────────────────

/**
 * Lấy trạng thái pipeline hiện tại của một meeting.
 * Dùng cho one-shot fetch; cho realtime xem `realtime.ts`.
 */
export async function getMeetingPipelineStatus(
  meetingId: string
): Promise<ApiResult<Pick<Meeting, 'id' | 'status' | 'error_message' | 'updated_at'>>> {
  try {
    const client = ensureClient();
    const { data, error } = await client
      .from('meetings')
      .select('id, status, error_message, updated_at')
      .eq('id', meetingId)
      .single();

    if (error) throw error;
    return { data: data as Pick<Meeting, 'id' | 'status' | 'error_message' | 'updated_at'>, error: null };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`[C9] Lấy pipeline status thất bại: ${message}`);
  }
}

// ─── H1 – View Meetings History ─────────────────────────

/**
 * Lấy danh sách meetings có phân trang (limit/offset).
 * Sắp xếp theo `created_at` mới nhất.
 */
export async function listMeetings(
  params: ListMeetingsParams = {}
): Promise<ApiResult<MeetingsListResult>> {
  const { limit = 20, offset = 0 } = params;

  try {
    const client = ensureClient();

    // Fetch paginated items
    const { data, error, count } = await client
      .from('meetings')
      .select('id, title, status, audio_duration_seconds, created_at, updated_at, jira_links_count', { count: 'exact' })
      .order('created_at', { ascending: false })
      .range(offset, offset + limit - 1);

    if (error) throw error;

    return {
      data: {
        items: (data ?? []) as MeetingsListResult['items'],
        total: count ?? 0,
      },
      error: null,
    };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`[H1] Lấy lịch sử meetings thất bại: ${message}`);
  }
}

// ─── H4 – View Old Meeting Detail ───────────────────────

/**
 * Lấy toàn bộ chi tiết của một meeting cũ bao gồm:
 * transcript segments, analysis result, và action items.
 */
export async function getMeetingDetail(
  meetingId: string
): Promise<ApiResult<MeetingDetailResult>> {
  try {
    const client = ensureClient();

    // Parallel fetch all related data
    const [meetingRes, segmentsRes, analysisRes, itemsRes] = await Promise.all([
      client
        .from('meetings')
        .select('*')
        .eq('id', meetingId)
        .single(),
      client
        .from('transcript_segments')
        .select('*')
        .eq('meeting_id', meetingId)
        .order('start_time', { ascending: true }),
      client
        .from('analysis_results')
        .select('*')
        .eq('meeting_id', meetingId)
        .order('created_at', { ascending: false })
        .limit(1)
        .maybeSingle(),
      client
        .from('action_items')
        .select('*')
        .eq('meeting_id', meetingId)
        .order('created_at', { ascending: true }),
    ]);

    if (meetingRes.error) throw meetingRes.error;

    return {
      data: {
        meeting: meetingRes.data as Meeting,
        analysis_result: (analysisRes.data as AnalysisResult) ?? null,
        transcript_segments: (segmentsRes.data ?? []) as TranscriptSegment[],
        action_items: (itemsRes.data ?? []) as ActionItem[],
      },
      error: null,
    };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`[H4] Lấy chi tiết meeting thất bại: ${message}`);
  }
}

// ─── H5 – Delete Meeting ────────────────────────────────

/**
 * Xoá meeting theo ID. RLS đảm bảo chỉ owner mới xoá được.
 * Cascade delete sẽ do DB đảm nhận (transcript_segments, analysis_results, action_items).
 */
export async function deleteMeeting(
  meetingId: string
): Promise<ApiResult<{ deleted: boolean }>> {
  try {
    const client = ensureClient();
    const { error } = await client
      .from('meetings')
      .delete()
      .eq('id', meetingId);

    if (error) throw error;
    return { data: { deleted: true }, error: null };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`[H5] Xoá meeting thất bại: ${message}`);
  }
}
