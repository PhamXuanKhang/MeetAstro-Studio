import { create } from 'zustand'
import { supabaseAuth } from '../auth/supabaseAuth'
import type { UserSession } from '../auth/authAdapter'

interface AuthState {
  user: UserSession | null
  loading: boolean
  initialized: boolean
}

interface AuthActions {
  initialize: () => Promise<void>
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, name?: string) => Promise<{ message?: string }>
  forgotPassword: (email: string) => Promise<void>
  logout: () => Promise<void>
}

let unsubscribeAuth: (() => void) | null = null

export const useAuthStore = create<AuthState & AuthActions>((set) => ({
  user: null,
  loading: false,
  initialized: false,

  initialize: async () => {
    set({ loading: true })
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
      set({ loading: false })
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

  logout: async () => {
    set({ loading: true })
    try {
      await supabaseAuth.logout()
    } finally {
      set({ user: null, loading: false })
    }
  },
}))
