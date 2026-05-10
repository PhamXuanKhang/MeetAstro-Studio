/**
 * useMeetings – React Query hooks for Supabase Meetings API
 * ---
 * Wraps src/api/supabase/meetings.api.ts functions with
 * TanStack Query for caching, loading states, and mutations.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  listMeetings,
  deleteMeeting,
} from '../../api/supabase/meetings.api'
import type { ListMeetingsParams, MeetingsListResult } from '../../types/supabase-models'

// ─── Query Keys ─────────────────────────────────────────

export const meetingKeys = {
  all: ['meetings'] as const,
  lists: () => [...meetingKeys.all, 'list'] as const,
  list: (params?: ListMeetingsParams) => [...meetingKeys.lists(), params ?? {}] as const,
}

// ─── useMeetingsList ────────────────────────────────────

/**
 * Lấy danh sách meetings có phân trang.
 *
 * @example
 * const { data, isLoading, error, refetch } = useMeetingsList({ limit: 20 });
 * // data.items — mảng meetings
 * // data.total — tổng số meetings
 */
export function useMeetingsList(params?: ListMeetingsParams) {
  return useQuery<MeetingsListResult, Error>({
    queryKey: meetingKeys.list(params),
    queryFn: () => listMeetings(params),
  })
}

// ─── useDeleteMeeting ───────────────────────────────────

/**
 * Mutation xoá meeting.
 * Tự invalidate list cache sau khi xoá thành công.
 *
 * @example
 * const { mutate: remove, isPending } = useDeleteMeeting();
 * remove(meetingId);
 */
export function useDeleteMeeting() {
  const queryClient = useQueryClient()

  return useMutation<{ deleted: boolean }, Error, string>({
    mutationFn: (meetingId: string) => deleteMeeting(meetingId),
    onSuccess: () => {
      // Invalidate tất cả list queries để UI refetch
      queryClient.invalidateQueries({ queryKey: meetingKeys.lists() })
    },
  })
}
