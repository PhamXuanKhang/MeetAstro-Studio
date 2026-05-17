/**
 * useTranscript – React Query hooks for Supabase Transcript API
 * ---
 * Wraps src/api/supabase/transcript.api.ts functions with
 * TanStack Query for caching, loading states, and mutations.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getTranscriptSegments,
  renameSpeaker,
  editTranscriptSegment,
} from '../../api/supabase/transcript.api'
import type {
  TranscriptSegment,
  RenameSpeakerPayload,
  EditTranscriptPayload,
} from '../../types/supabase-models'

// ─── Query Keys ─────────────────────────────────────────

export const transcriptKeys = {
  all: ['transcript'] as const,
  segments: (meetingId: string) => [...transcriptKeys.all, 'segments', meetingId] as const,
}

// ─── useTranscriptSegments ──────────────────────────────

/**
 * Lấy danh sách transcript segments của một meeting.
 *
 * @example
 * const { data, isLoading } = useTranscriptSegments(meetingId);
 * // data.segments — mảng TranscriptSegment[]
 */
export function useTranscriptSegments(meetingId: string | null) {
  return useQuery<{ segments: TranscriptSegment[] }, Error>({
    queryKey: transcriptKeys.segments(meetingId ?? ''),
    queryFn: () => getTranscriptSegments(meetingId!),
    enabled: !!meetingId,
  })
}

// ─── useEditTranscriptSegment ───────────────────────────

/**
 * Mutation chỉnh sửa nội dung text của một transcript segment.
 * Tự invalidate transcript cache sau khi sửa thành công.
 *
 * @example
 * const { mutate: edit } = useEditTranscriptSegment(meetingId);
 * edit({ segment_id: '...', content: 'new text' });
 */
export function useEditTranscriptSegment(meetingId: string | null) {
  const queryClient = useQueryClient()

  return useMutation<
    { segment: Pick<TranscriptSegment, 'id' | 'content'> },
    Error,
    EditTranscriptPayload
  >({
    mutationFn: (payload) => editTranscriptSegment(payload),
    onSuccess: () => {
      if (meetingId) {
        queryClient.invalidateQueries({ queryKey: transcriptKeys.segments(meetingId) })
      }
    },
  })
}

// ─── useRenameSpeaker ───────────────────────────────────

/**
 * Mutation đổi tên speaker trong tất cả transcript segments.
 * Tự invalidate transcript cache sau khi đổi thành công.
 *
 * @example
 * const { mutate: rename } = useRenameSpeaker(meetingId);
 * rename({ meeting_id: '...', from_speaker: 'Speaker A', to_speaker: 'Khang' });
 */
export function useRenameSpeaker(meetingId: string | null) {
  const queryClient = useQueryClient()

  return useMutation<{ updated_count: number }, Error, RenameSpeakerPayload>({
    mutationFn: (payload) => renameSpeaker(payload),
    onSuccess: () => {
      if (meetingId) {
        queryClient.invalidateQueries({ queryKey: transcriptKeys.segments(meetingId) })
      }
    },
  })
}
