import axios, { AxiosInstance } from 'axios'
import { useAuthStore } from '../store/authStore'

let _baseURL = 'http://localhost:8000'

// Allow updating the base URL at runtime (from Settings or electron IPC)
export function setApiBaseUrl(url: string) {
  _baseURL = url.replace(/\/$/, '')
  _client = createClient()
}

export function getApiBaseUrl(): string {
  return _baseURL
}

export function getCurrentUserId(): string {
  const userId = useAuthStore.getState().user?.userId
  if (!userId) throw new Error('Bạn cần đăng nhập trước khi gọi API này.')
  return userId
}

function createClient(): AxiosInstance {
  const instance = axios.create({
    baseURL: `${_baseURL}/api/v1`,
    timeout: 60000,
    headers: {
      'Content-Type': 'application/json',
    },
  })

  instance.interceptors.request.use((config) => {
    const accessToken = useAuthStore.getState().user?.accessToken
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`
    }
    return config
  })

  instance.interceptors.response.use(
    (res) => res,
    (err) => {
      const msg = err.response?.data?.detail || err.response?.data?.message || err.message
      return Promise.reject(new Error(String(msg)))
    }
  )

  return instance
}

let _client: AxiosInstance = createClient()

export function getClient(): AxiosInstance {
  return _client
}

// Attempt to read API URL from Electron IPC on startup
if (typeof window !== 'undefined' && (window as unknown as { electronAPI?: { getApiUrl: () => Promise<string> } }).electronAPI) {
  ;(window as unknown as { electronAPI: { getApiUrl: () => Promise<string> } }).electronAPI
    .getApiUrl()
    .then((url) => {
      if (url) setApiBaseUrl(url)
    })
    .catch(() => {})
}
