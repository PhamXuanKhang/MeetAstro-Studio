/**
 * Realtime Subscriptions – Supabase SDK
 * Covers: C9, D1, G2
 */

import { supabase } from '../../lib/supabase';
import type { RealtimeChannel, RealtimePostgresChangesPayload } from '@supabase/supabase-js';
import type { Meeting, TranscriptSegment, ActionItem } from '../../types/supabase-models';

function ensureClient() {
  if (!supabase) throw new Error('Supabase client not initialized.');
  return supabase;
}

/** C9 – Subscribe to meeting pipeline status changes. */
export function subscribeMeetingStatus(
  meetingId: string,
  onUpdate: (p: Pick<Meeting, 'id' | 'status' | 'error_message' | 'updated_at'>) => void
): RealtimeChannel {
  const client = ensureClient();
  return client
    .channel(`meeting-status:${meetingId}`)
    .on('postgres_changes', {
      event: 'UPDATE', schema: 'public', table: 'meetings',
      filter: `id=eq.${meetingId}`,
    }, (payload: RealtimePostgresChangesPayload<Record<string, unknown>>) => {
      const r = payload.new as Record<string, unknown>;
      onUpdate({
        id: r.id as string,
        status: r.status as Meeting['status'],
        error_message: (r.error_message as string) ?? null,
        updated_at: r.updated_at as string,
      });
    })
    .subscribe();
}

/** D1 – Subscribe to new transcript segments (live). */
export function subscribeTranscriptSegments(
  meetingId: string,
  onInsert: (segment: TranscriptSegment) => void
): RealtimeChannel {
  const client = ensureClient();
  return client
    .channel(`transcript:${meetingId}`)
    .on('postgres_changes', {
      event: 'INSERT', schema: 'public', table: 'transcript_segments',
      filter: `meeting_id=eq.${meetingId}`,
    }, (payload: RealtimePostgresChangesPayload<Record<string, unknown>>) => {
      const r = payload.new as Record<string, unknown>;
      onInsert({
        id: r.id as string, meeting_id: r.meeting_id as string,
        speaker: r.speaker as string, start_time: r.start_time as number,
        end_time: r.end_time as number, content: r.content as string,
      });
    })
    .subscribe();
}

/** G2 – Subscribe to action item sync status changes. */
export function subscribeActionItemSyncStatus(
  meetingId: string,
  onUpdate: (item: Pick<ActionItem, 'id' | 'sync_status' | 'sync_error' | 'jira_issue_key' | 'jira_issue_url'>) => void
): RealtimeChannel {
  const client = ensureClient();
  return client
    .channel(`push-status:${meetingId}`)
    .on('postgres_changes', {
      event: 'UPDATE', schema: 'public', table: 'action_items',
      filter: `meeting_id=eq.${meetingId}`,
    }, (payload: RealtimePostgresChangesPayload<Record<string, unknown>>) => {
      const r = payload.new as Record<string, unknown>;
      onUpdate({
        id: r.id as string,
        sync_status: r.sync_status as ActionItem['sync_status'],
        sync_error: (r.sync_error as string) ?? null,
        jira_issue_key: (r.jira_issue_key as string) ?? null,
        jira_issue_url: (r.jira_issue_url as string) ?? null,
      });
    })
    .subscribe();
}

/** Safely unsubscribe a realtime channel. */
export async function unsubscribeChannel(channel: RealtimeChannel | null): Promise<void> {
  if (!channel) return;
  try {
    ensureClient().removeChannel(channel);
  } catch { /* already removed */ }
}
