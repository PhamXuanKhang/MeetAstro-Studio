import { create } from 'zustand'
import { supabaseAuth } from '../auth/supabaseAuth'
import { parseAuthDeepLink } from '../auth/deepLink'
import type { UserSession } from '../auth/authAdapter'

interface AuthState {
  user: UserSession | null
  loading: boolean
  initializing: boolean
  initialized: boolean
}

interface AuthActions {
  initialize: () => Promise<void>
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, name?: string) => Promise<{ message?: string }>
  forgotPassword: (email: string) => Promise<void>
  startGoogleOAuth: () => Promise<void>
  handleAuthCallback: (url: string) => Promise<{ route?: 'reset'; error?: string }>
  updatePassword: (newPassword: string) => Promise<void>
  logout: () => Promise<void>
}

let unsubscribeAuth: (() => void) | null = null

export const useAuthStore = create<AuthState & AuthActions>((set) => ({
  user: null,
  loading: false,
  initializing: false,
  initialized: false,

  initialize: async () => {
    set({ initializing: true })
    try {
      const user = await supabaseAuth.getSession()
      unsubscribeAuth?.()
      unsubscribeAuth = supabaseAuth.onAuthStateChange((updatedUser) => {
        set({ user: updatedUser })
      })
      set({ user, initialized: true })
    } catch {
      set({ user: null, initialized: true })
    } finally {
      set({ initializing: false })
    }
  },

  login: async (email, password) => {
    set({ loading: true })
    try {
      const { session } = await supabaseAuth.login(email, password)
      set({ user: session })
    } finally {
      set({ loading: false })
    }
  },

  register: async (email, password, name) => {
    set({ loading: true })
    try {
      const { session, message } = await supabaseAuth.register(email, password, name)
      if (session) set({ user: session })
      return { message }
    } finally {
      set({ loading: false })
    }
  },

  forgotPassword: async (email) => {
    set({ loading: true })
    try {
      await supabaseAuth.forgotPassword(email)
    } finally {
      set({ loading: false })
    }
  },

  startGoogleOAuth: async () => {
    set({ loading: true })
    try {
      if (!window.electronAPI?.openExternalAuthUrl) {
        throw new Error('Electron auth IPC chưa sẵn sàng.')
      }
      const { url } = await supabaseAuth.getOAuthUrl('google', 'meetastro://auth/callback')
      await window.electronAPI.openExternalAuthUrl(url)
    } finally {
      set({ loading: false })
    }
  },

  handleAuthCallback: async (url) => {
    const result = parseAuthDeepLink(url)
    const message = result.errorDescription || result.error
    if (message) return { error: message }
    if (!result.accessToken || !result.refreshToken) return { error: 'Callback đăng nhập không hợp lệ.' }

    try {
      const user = await supabaseAuth.setSession(result.accessToken, result.refreshToken)
      set({ user })
      if (result.type === 'password_recovery') return { route: 'reset' }
      return {}
    } catch (err) {
      return { error: err instanceof Error ? err.message : 'Không xử lý được callback đăng nhập.' }
    }
  },

  updatePassword: async (newPassword) => {
    set({ loading: true })
    try {
      await supabaseAuth.updatePassword(newPassword)
      const user = await supabaseAuth.getSession()
      set({ user })
    } finally {
      set({ loading: false })
    }
  },

  logout: async () => {
    set({ loading: true })
    try {
      await supabaseAuth.logout()
    } finally {
      set({ user: null, loading: false })
    }
  },
}))
