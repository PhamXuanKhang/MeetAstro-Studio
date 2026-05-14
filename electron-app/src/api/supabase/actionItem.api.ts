/**
 * Action Items – Supabase SDK Data Access Layer
 * ---
 * Covers use cases: F1, F5, F6, F8
 * Contract: docs/backend-contract-v1.md
 *
 * Error strategy: throw on failure (consistent with existing axios API layer).
 */

import { supabase } from '../../lib/supabase';
import { getClient } from '../client';
import type {
  ActionItem,
  EditActionItemPayload,
  ApproveActionItemPayload,
  RejectActionItemPayload,
  AddManualActionItemPayload,
} from '../../types/supabase-models';

// ─── Helpers ─────────────────────────────────────────────

function ensureClient() {
  if (!supabase) {
    throw new Error('Supabase client chưa được khởi tạo. Kiểm tra biến môi trường VITE_SUPABASE_URL và VITE_SUPABASE_ANON_KEY.');
  }
  return supabase;
}

// ─── List Action Items (for ReviewView) ─────────────────

/**
 * Lấy tất cả action items của một meeting.
 * Sắp xếp theo created_at tăng dần.
 */
export async function listActionItems(
  meetingId: string
): Promise<ActionItem[]> {
  try {
    const client = ensureClient();
    const { data, error } = await client
      .from('action_items')
      .select('*')
      .eq('meeting_id', meetingId)
      .order('created_at', { ascending: true });

    if (error) throw error;
    return (data ?? []) as ActionItem[];
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`Lấy action items thất bại: ${message}`);
  }
}

// ─── Bulk Approve (ReviewView "Approve All") ────────────

/**
 * Approve tất cả action items đang ở trạng thái 'draft' hoặc 'edited'.
 * Trả về số lượng items đã được approve.
 */
export async function bulkApproveActionItems(
  meetingId: string
): Promise<{ approved_count: number }> {
  try {
    const client = ensureClient();
    const { data, error } = await client
      .from('action_items')
      .update({ review_status: 'approved', is_selected: true })
      .eq('meeting_id', meetingId)
      .in('review_status', ['draft', 'edited'])
      .neq('sync_status', 'synced')
      .select('id');

    if (error) throw error;
    return { approved_count: data?.length ?? 0 };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`Bulk approve thất bại: ${message}`);
  }
}

// ─── F1 – Edit Epic/Task/Subtask ────────────────────────

/**
 * Cập nhật các trường editable của một action item.
 * Có thể sửa title, description, assignee, deadline, priority, review_status.
 */
export async function editActionItem(
  payload: EditActionItemPayload
): Promise<{ action_item: Pick<ActionItem, 'id' | 'review_status'> }> {
  const { action_item_id, ...updates } = payload;

  try {
    const client = ensureClient();
    const { data, error } = await client
      .from('action_items')
      .update(updates)
      .eq('id', action_item_id)
      .select('id, review_status')
      .single();

    if (error) throw error;

    return { action_item: data as Pick<ActionItem, 'id' | 'review_status'> };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`[F1] Chỉnh sửa action item thất bại: ${message}`);
  }
}

// ─── F5 – Approve Action Item ───────────────────────────

/**
 * Duyệt một action item: set review_status = 'approved', is_selected = true.
 */
export async function approveActionItem(
  payload: ApproveActionItemPayload
): Promise<{ action_item: Pick<ActionItem, 'id' | 'review_status' | 'is_selected'> }> {
  const { action_item_id } = payload;

  try {
    const client = ensureClient();
    const { data, error } = await client
      .from('action_items')
      .update({
        review_status: 'approved',
        is_selected: true,
      })
      .eq('id', action_item_id)
      .select('id, review_status, is_selected')
      .single();

    if (error) throw error;

    return { action_item: data as Pick<ActionItem, 'id' | 'review_status' | 'is_selected'> };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`[F5] Duyệt action item thất bại: ${message}`);
  }
}

// ─── F6 – Reject Action Item ────────────────────────────

/**
 * Từ chối một action item: set review_status = 'rejected', is_selected = false.
 */
export async function rejectActionItem(
  payload: RejectActionItemPayload
): Promise<{ action_item: Pick<ActionItem, 'id' | 'review_status' | 'is_selected'> }> {
  const { action_item_id } = payload;

  try {
    const client = ensureClient();
    const { data, error } = await client
      .from('action_items')
      .update({
        review_status: 'rejected',
        is_selected: false,
      })
      .eq('id', action_item_id)
      .select('id, review_status, is_selected')
      .single();

    if (error) throw error;

    return { action_item: data as Pick<ActionItem, 'id' | 'review_status' | 'is_selected'> };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`[F6] Từ chối action item thất bại: ${message}`);
  }
}

// ─── F8 – Add Manual Action Item ────────────────────────

/**
 * Tạo action item thủ công (do user nhập, không phải AI extract).
 * Mặc định confidence_score = 1.0, review_status = 'approved'.
 */
export async function addManualActionItem(
  payload: AddManualActionItemPayload
): Promise<{ action_item: Pick<ActionItem, 'id' | 'title'> }> {
  try {
    const { meeting_id, ...body } = payload;
    const { data } = await getClient().post<{ id: string; summary: string }>(
      `/meetings/${meeting_id}/review`,
      body
    );

    return { action_item: { id: data.id, title: data.summary } };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`[F8] Thêm action item thủ công thất bại: ${message}`);
  }
}
