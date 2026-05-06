import { DEFAULT_USER_ID, getClient } from './client'
import type { ProviderListResponse } from '../types/schema'

export async function listProviderConfigs(userId = DEFAULT_USER_ID): Promise<string[]> {
  const { data } = await getClient().get<ProviderListResponse>('/settings/providers', {
    params: { user_id: userId },
  })
  return data.providers
}

export async function setProviderConfig(
  providerName: string,
  config: Record<string, string>,
  userId = DEFAULT_USER_ID
): Promise<void> {
  await getClient().post(`/settings/providers/${providerName}`, { config, user_id: userId })
}

export async function deleteProviderConfig(
  providerName: string,
  userId = DEFAULT_USER_ID
): Promise<void> {
  await getClient().delete(`/settings/providers/${providerName}`, {
    params: { user_id: userId },
  })
}
