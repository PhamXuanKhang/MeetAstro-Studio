/**
 * Analysis – Supabase SDK Data Access Layer
 * ---
 * Covers use cases: E2, E3, E6
 * (E1 – Trigger Analysis is FastAPI, handled elsewhere)
 * Contract: docs/backend-contract-v1.md
 *
 * Error strategy: throw on failure (consistent with existing axios API layer).
 */

import { supabase } from '../../lib/supabase';
import type {
  AnalysisResult,
  ActionItem,
  AnalysisWithItemsResult,
  ConfidenceScoreItem,
} from '../../types/supabase-models';

// ─── Helpers ─────────────────────────────────────────────

function ensureClient() {
  if (!supabase) {
    throw new Error('Supabase client chưa được khởi tạo. Kiểm tra biến môi trường VITE_SUPABASE_URL và VITE_SUPABASE_ANON_KEY.');
  }
  return supabase;
}

// ─── E2 – View Meeting Summary ──────────────────────────

/**
 * Lấy summary ngắn gọn của analysis result.
 * Chỉ trả về `summary_text` — dùng cho dashboard/list view.
 */
export async function getMeetingSummary(
  meetingId: string
): Promise<{ analysis_result: Pick<AnalysisResult, 'summary_text'> | null }> {
  try {
    const client = ensureClient();
    const { data, error } = await client
      .from('analysis_results')
      .select('summary_text')
      .eq('meeting_id', meetingId)
      .order('created_at', { ascending: false })
      .limit(1)
      .maybeSingle();

    if (error) throw error;

    return {
      analysis_result: data
        ? { summary_text: (data as { summary_text: string }).summary_text }
        : null,
    };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`[E2] Lấy meeting summary thất bại: ${message}`);
  }
}

// ─── E3 – View Analysis Result ──────────────────────────

/**
 * Lấy kết quả phân tích đầy đủ cùng danh sách action items.
 */
export async function getAnalysisResult(
  meetingId: string
): Promise<AnalysisWithItemsResult> {
  try {
    const client = ensureClient();

    const [analysisRes, itemsRes] = await Promise.all([
      client
        .from('analysis_results')
        .select('summary_text, key_decisions, parking_lot, raw_response')
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

    if (analysisRes.error) throw analysisRes.error;
    if (itemsRes.error) throw itemsRes.error;

    return {
      data: {
        analysis_result: (analysisRes.data as AnalysisResult | null) ?? null,
        action_items: (itemsRes.data ?? []) as ActionItem[],
      },
      error: null,
    };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`[E3] Lấy analysis result thất bại: ${message}`);
  }
}

// ─── E6 – View Confidence Score ─────────────────────────

/**
 * Lấy confidence score của tất cả action items thuộc một meeting.
 * Dùng để hiển thị mức độ tin cậy của AI extraction.
 */
export async function getConfidenceScores(
  meetingId: string
): Promise<{ action_items: ConfidenceScoreItem[] }> {
  try {
    const client = ensureClient();
    const { data, error } = await client
      .from('action_items')
      .select('id, title, confidence_score')
      .eq('meeting_id', meetingId)
      .order('confidence_score', { ascending: true });

    if (error) throw error;

    return { action_items: (data ?? []) as ConfidenceScoreItem[] };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`[E6] Lấy confidence scores thất bại: ${message}`);
  }
}
