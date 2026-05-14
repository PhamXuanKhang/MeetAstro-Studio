const DEFAULT_API_BASE_URL = 'http://localhost:8000'

export function normalizeApiBaseUrl(url?: string): string {
  const trimmed = url?.trim()
  return (trimmed || DEFAULT_API_BASE_URL).replace(/\/+$/, '')
}

export const API_BASE_URL = normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL)
