import { getClient, getCurrentUserId } from './client'
import type { ProviderListResponse } from '../types/supabase-models'

export interface ProviderConfigStatus {
  provider_name: string
  is_configured: boolean
  masked_key: string | null
}

export async function listProviderConfigs(userId = getCurrentUserId()): Promise<string[]> {
  const { data } = await getClient().get<ProviderListResponse>('/settings/providers', {
    params: { user_id: userId },
  })
  return data.providers
}

export async function getProviderConfigStatus(
  providerName: string,
  userId = getCurrentUserId()
): Promise<ProviderConfigStatus> {
  const { data } = await getClient().get<ProviderConfigStatus>(`/settings/providers/${providerName}`, {
    params: { user_id: userId },
  })
  return data
}

export async function setProviderConfig(
  providerName: string,
  config: Record<string, unknown>,
  userId = getCurrentUserId()
): Promise<ProviderConfigStatus> {
  const { data } = await getClient().post<ProviderConfigStatus>(`/settings/providers/${providerName}`, {
    config,
    user_id: userId,
  })
  return data
}

export async function saveProviderApiKey(
  providerName: string,
  apiKey: string,
  configData: Record<string, unknown> = {},
  userId = getCurrentUserId()
): Promise<ProviderConfigStatus> {
  const { data } = await getClient().post<ProviderConfigStatus>(`/settings/providers/${providerName}`, {
    api_key: apiKey,
    config_data: configData,
    user_id: userId,
  })
  return data
}

export async function deleteProviderConfig(
  providerName: string,
  userId = getCurrentUserId()
): Promise<void> {
  await getClient().delete(`/settings/providers/${providerName}`, {
    params: { user_id: userId },
  })
}
