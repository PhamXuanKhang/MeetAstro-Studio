import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  deleteProviderConfig,
  getProviderConfigStatus,
  setProviderConfig,
  type ProviderConfigStatus,
} from '../api/settings'

const providerStatusKey = (providerName: string) => ['provider-config-status', providerName] as const

export function useProviderConfigStatus(providerName: string) {
  return useQuery<ProviderConfigStatus, Error>({
    queryKey: providerStatusKey(providerName),
    queryFn: () => getProviderConfigStatus(providerName),
  })
}

export function useSaveProviderConfig(providerName: string) {
  const queryClient = useQueryClient()

  return useMutation<ProviderConfigStatus, Error, Record<string, unknown>>({
    mutationFn: (config) => setProviderConfig(providerName, config),
    onSuccess: (status) => {
      queryClient.setQueryData(providerStatusKey(providerName), status)
      void queryClient.invalidateQueries({ queryKey: providerStatusKey(providerName) })
    },
  })
}

export function useDeleteProviderConfig(providerName: string) {
  const queryClient = useQueryClient()

  return useMutation<void, Error>({
    mutationFn: () => deleteProviderConfig(providerName),
    onSuccess: () => {
      queryClient.setQueryData(providerStatusKey(providerName), {
        provider_name: providerName,
        is_configured: false,
        masked_key: null,
      })
    },
  })
}
