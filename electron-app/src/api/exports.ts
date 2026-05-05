import { getClient } from './client'

export async function exportMarkdown(meetingId: string): Promise<string> {
  const { data } = await getClient().get<string>(`/meetings/${meetingId}/export/markdown`, {
    responseType: 'text',
  })
  return data
}

export async function exportJson(meetingId: string): Promise<string> {
  const { data } = await getClient().get<string>(`/meetings/${meetingId}/export/json`, {
    responseType: 'text',
  })
  return data
}

export async function exportCsv(meetingId: string): Promise<string> {
  const { data } = await getClient().get<string>(`/meetings/${meetingId}/export/csv`, {
    responseType: 'text',
  })
  return data
}
