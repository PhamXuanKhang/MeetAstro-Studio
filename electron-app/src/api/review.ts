import { getClient } from './client'
import type { ReviewItemResponse, ReviewSummaryResponse } from '../types/schema'

export async function listReviewItems(meetingId: string): Promise<ReviewItemResponse[]> {
  const { data } = await getClient().get<ReviewItemResponse[]>(`/meetings/${meetingId}/review`)
  return data
}

export async function getReviewSummary(meetingId: string): Promise<ReviewSummaryResponse> {
  const { data } = await getClient().get<ReviewSummaryResponse>(
    `/meetings/${meetingId}/review/summary`
  )
  return data
}

export async function patchReviewItem(
  meetingId: string,
  itemId: string,
  updates: {
    edited_summary?: string | null
    edited_assignee?: string | null
    edited_deadline?: string | null
    edited_priority?: string | null
  }
): Promise<ReviewItemResponse> {
  const { data } = await getClient().patch<ReviewItemResponse>(
    `/meetings/${meetingId}/review/${itemId}`,
    updates
  )
  return data
}

export async function approveItem(meetingId: string, itemId: string): Promise<ReviewItemResponse> {
  const { data } = await getClient().post<ReviewItemResponse>(
    `/meetings/${meetingId}/review/${itemId}/approve`
  )
  return data
}

export async function rejectItem(meetingId: string, itemId: string): Promise<ReviewItemResponse> {
  const { data } = await getClient().post<ReviewItemResponse>(
    `/meetings/${meetingId}/review/${itemId}/reject`
  )
  return data
}

export async function approveAll(meetingId: string): Promise<{ approved_count: number }> {
  const { data } = await getClient().post<{ approved_count: number }>(
    `/meetings/${meetingId}/review/approve_all`
  )
  return data
}
