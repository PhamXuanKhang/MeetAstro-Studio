/**
 * Transcript – Supabase SDK Data Access Layer
 * ---
 * Covers use cases: D2, D3, D4, D5
 * (D1 – Realtime transcript subscription is in realtime.ts)
 * Contract: docs/backend-contract-v1.md
 *
 * Error strategy: throw on failure (consistent with existing axios API layer).
 */

import { supabase } from '../../lib/supabase';
import type {
  TranscriptSegment,
  RenameSpeakerPayload,
  EditTranscriptPayload,
} from '../../types/supabase-models';

// ─── Helpers ─────────────────────────────────────────────

function ensureClient() {
  if (!supabase) {
    throw new Error('Supabase client chưa được khởi tạo. Kiểm tra biến môi trường VITE_SUPABASE_URL và VITE_SUPABASE_ANON_KEY.');
  }
  return supabase;
}

// ─── D2 – View Final Transcript ─────────────────────────

/**
 * Lấy toàn bộ transcript segments đã hoàn chỉnh của một meeting.
 * Sắp xếp theo thời gian bắt đầu (start_time) tăng dần.
 */
export async function getTranscriptSegments(
  meetingId: string
): Promise<{ segments: TranscriptSegment[] }> {
  try {
    const client = ensureClient();
    const { data, error } = await client
      .from('transcript_segments')
      .select('id, meeting_id, speaker, start_time, end_time, content')
      .eq('meeting_id', meetingId)
      .order('start_time', { ascending: true });

    if (error) throw error;

    return { segments: (data ?? []) as TranscriptSegment[] };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`[D2] Lấy transcript thất bại: ${message}`);
  }
}

// ─── D3 – View Diarization ──────────────────────────────

/**
 * Lấy diarization data — cùng dữ liệu transcript nhưng nhóm theo speaker.
 * Contract trả về tương tự D2 nhưng không kèm `id` segment.
 */
export async function getDiarization(
  meetingId: string
): Promise<{ segments: Omit<TranscriptSegment, 'id' | 'meeting_id'>[] }> {
  try {
    const client = ensureClient();
    const { data, error } = await client
      .from('transcript_segments')
      .select('speaker, start_time, end_time, content')
      .eq('meeting_id', meetingId)
      .order('start_time', { ascending: true });

    if (error) throw error;

    return {
      segments: (data ?? []) as Omit<TranscriptSegment, 'id' | 'meeting_id'>[],
    };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`[D3] Lấy diarization thất bại: ${message}`);
  }
}

// ─── D4 – Rename Speaker ────────────────────────────────

/**
 * Đổi tên speaker trong tất cả transcript segments thuộc một meeting.
 * Trả về số segments đã cập nhật (`updated_count`).
 */
export async function renameSpeaker(
  payload: RenameSpeakerPayload
): Promise<{ updated_count: number }> {
  const { meeting_id, from_speaker, to_speaker } = payload;

  try {
    const client = ensureClient();

    // Supabase .update() trả count qua select() với option count
    const { data: updated, error } = await client
      .from('transcript_segments')
      .update({ speaker: to_speaker })
      .eq('meeting_id', meeting_id)
      .eq('speaker', from_speaker)
      .select('id');

    if (error) throw error;

    return { updated_count: updated?.length ?? 0 };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`[D4] Rename speaker thất bại: ${message}`);
  }
}

// ─── D5 – Edit Transcript Text ──────────────────────────

/**
 * Chỉnh sửa nội dung text của một transcript segment cụ thể.
 */
export async function editTranscriptSegment(
  payload: EditTranscriptPayload
): Promise<{ segment: Pick<TranscriptSegment, 'id' | 'content'> }> {
  const { segment_id, content } = payload;

  try {
    const client = ensureClient();
    const { data, error } = await client
      .from('transcript_segments')
      .update({ content })
      .eq('id', segment_id)
      .select('id, content')
      .single();

    if (error) throw error;

    return { segment: data as Pick<TranscriptSegment, 'id' | 'content'> };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`[D5] Chỉnh sửa transcript thất bại: ${message}`);
  }
}
