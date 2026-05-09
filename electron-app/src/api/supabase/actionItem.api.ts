/**
 * Action Items – Supabase SDK Data Access Layer
 * ---
 * Covers use cases: F1, F5, F6, F8
 * Contract: docs/backend-contract-v1.md
 *
 * Error strategy: throw on failure (consistent with existing axios API layer).
 */

import { supabase } from '../../lib/supabase';
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
 * Mặc định confidence_score = 1.0, review_status = 'edited'.
 */
export async function addManualActionItem(
  payload: AddManualActionItemPayload
): Promise<{ action_item: Pick<ActionItem, 'id' | 'title'> }> {
  try {
    const client = ensureClient();
    const { data, error } = await client
      .from('action_items')
      .insert({
        meeting_id: payload.meeting_id,
        parent_id: payload.parent_id ?? null,
        item_type: payload.item_type,
        title: payload.title,
        description: payload.description ?? '',
        assignee: payload.assignee ?? null,
        deadline: payload.deadline ?? null,
        priority: payload.priority ?? 'medium',
        context: payload.context ?? 'Manual item',
        confidence_score: payload.confidence_score ?? 1.0,
        review_status: payload.review_status ?? 'edited',
        is_selected: payload.is_selected ?? false,
        sync_status: payload.sync_status ?? 'pending',
      })
      .select('id, title')
      .single();

    if (error) throw error;

    return { action_item: data as Pick<ActionItem, 'id' | 'title'> };
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`[F8] Thêm action item thủ công thất bại: ${message}`);
  }
}
