import { getClient } from './client'
import type { ProviderListResponse } from '../types/schema'

export async function listProviderConfigs(userId = 'default_user'): Promise<string[]> {
  const { data } = await getClient().get<ProviderListResponse>('/settings/providers', {
    params: { user_id: userId },
  })
  return data.providers
}

export async function setProviderConfig(
  providerName: string,
  config: Record<string, string>,
  userId = 'default_user'
): Promise<void> {
  await getClient().post(`/settings/providers/${providerName}`, { config, user_id: userId })
}

export async function deleteProviderConfig(
  providerName: string,
  userId = 'default_user'
): Promise<void> {
  await getClient().delete(`/settings/providers/${providerName}`, {
    params: { user_id: userId },
  })
}
