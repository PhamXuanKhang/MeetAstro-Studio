/**
 * Jira Sync – Supabase SDK Data Access Layer
 * ---
 * Covers use cases: G4
 * (G1/G3 are FastAPI; G2 realtime subscription is in realtime.ts)
 * Contract: docs/backend-contract-v1.md
 */

import { supabase } from '../../lib/supabase';
import type {
  JiraIssueLink,
  ApiResult,
} from '../../types/supabase-models';

// ─── Helpers ─────────────────────────────────────────────

function ensureClient() {
  if (!supabase) {
    throw new Error('Supabase client chưa được khởi tạo. Kiểm tra biến môi trường VITE_SUPABASE_URL và VITE_SUPABASE_ANON_KEY.');
  }
  return supabase;
}

// ─── G4 – View Jira Issue Links ─────────────────────────

/**
 * Lấy danh sách Jira issue links của các action items đã push thành công.
 * Chỉ trả về items có `jira_issue_key` khác null.
 */
export async function getJiraIssueLinks(
  meetingId: string
): Promise<ApiResult<{ items: JiraIssueLink[] }>> {
  try {
    const client = ensureClient();
    const { data, error } = await client
      .from('action_items')
      .select('id, jira_issue_key, jira_issue_url')
      .eq('meeting_id', meetingId)
      .not('jira_issue_key', 'is', null);

    if (error) throw error;

    return {
      data: { items: (data ?? []) as JiraIssueLink[] },
      error: null,
    };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`[G4] Lấy Jira issue links thất bại: ${message}`);
  }
}
