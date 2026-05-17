import { getClient } from './client'
import { pollJob } from './jobs'
import type { JiraPushResponse } from '../types/supabase-models'

export async function pushToJira(
  meetingId: string,
  signal?: AbortSignal
): Promise<JiraPushResponse> {
  const { data } = await getClient().post<JiraPushResponse>(`/meetings/${meetingId}/jira/push`)

  if (data.job_id) {
    await pollJob(data.job_id, 120000, 2000, signal)
  }

  return data
}

export async function getJiraStatus(meetingId: string) {
  const { data } = await getClient().get(`/meetings/${meetingId}/jira/status`)
  return data
}
