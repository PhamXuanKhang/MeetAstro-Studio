/**
 * useActionItems – React Query hooks for Supabase Action Items API
 * ---
 * Wraps src/api/supabase/actionItem.api.ts functions with
 * TanStack Query for caching, loading states, and mutations.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  listActionItems,
  editActionItem,
  approveActionItem,
  rejectActionItem,
  bulkApproveActionItems,
} from '../../api/supabase/actionItem.api'
import type {
  ActionItem,
  EditActionItemPayload,
} from '../../types/supabase-models'

// ─── Query Keys ─────────────────────────────────────────

export const actionItemKeys = {
  all: ['actionItems'] as const,
  list: (meetingId: string) => [...actionItemKeys.all, 'list', meetingId] as const,
}

// ─── useActionItemsList ─────────────────────────────────

/**
 * Lấy danh sách action items của một meeting.
 *
 * @example
 * const { data: items, isLoading } = useActionItemsList(meetingId);
 */
export function useActionItemsList(meetingId: string | null) {
  return useQuery<ActionItem[], Error>({
    queryKey: actionItemKeys.list(meetingId ?? ''),
    queryFn: () => listActionItems(meetingId!),
    enabled: !!meetingId,
  })
}

// ─── useEditActionItem ──────────────────────────────────

/**
 * Mutation chỉnh sửa action item (title, description, assignee, deadline, priority).
 * Tự invalidate list cache sau khi sửa thành công.
 */
export function useEditActionItem(meetingId: string | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: EditActionItemPayload) => editActionItem(payload),
    onSuccess: () => {
      if (meetingId) {
        queryClient.invalidateQueries({ queryKey: actionItemKeys.list(meetingId) })
      }
    },
  })
}

// ─── useApproveActionItem ───────────────────────────────

/**
 * Mutation approve một action item.
 */
export function useApproveActionItem(meetingId: string | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (actionItemId: string) =>
      approveActionItem({ action_item_id: actionItemId, review_status: 'approved', is_selected: true }),
    onSuccess: () => {
      if (meetingId) {
        queryClient.invalidateQueries({ queryKey: actionItemKeys.list(meetingId) })
      }
    },
  })
}

// ─── useRejectActionItem ────────────────────────────────

/**
 * Mutation reject một action item.
 */
export function useRejectActionItem(meetingId: string | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (actionItemId: string) =>
      rejectActionItem({ action_item_id: actionItemId, review_status: 'rejected', is_selected: false }),
    onSuccess: () => {
      if (meetingId) {
        queryClient.invalidateQueries({ queryKey: actionItemKeys.list(meetingId) })
      }
    },
  })
}

// ─── useBulkApproveActionItems ──────────────────────────

/**
 * Mutation approve tất cả action items (draft/edited) trong một meeting.
 */
export function useBulkApproveActionItems(meetingId: string | null) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => bulkApproveActionItems(meetingId!),
    onSuccess: () => {
      if (meetingId) {
        queryClient.invalidateQueries({ queryKey: actionItemKeys.list(meetingId) })
      }
    },
  })
}
