import { supabase } from '../lib/supabase'
import type { AuthAdapter, AuthResult, UserSession } from './authAdapter'
import type { Session } from '@supabase/supabase-js'

function requireSupabase() {
  if (!supabase) {
    throw new Error('Supabase chưa được cấu hình. Vui lòng thêm VITE_SUPABASE_URL và VITE_SUPABASE_ANON_KEY vào .env.')
  }
  return supabase
}

function toUserSession(session: Session | null): UserSession | null {
  if (!session?.user) return null
  return {
    userId: session.user.id,
    email: session.user.email ?? '',
    name: typeof session.user.user_metadata?.name === 'string' ? session.user.user_metadata.name : null,
    accessToken: session.access_token,
  }
}

export const supabaseAuth: AuthAdapter = {
  async login(email: string, password: string): Promise<AuthResult> {
    const client = requireSupabase()
    const { data, error } = await client.auth.signInWithPassword({ email, password })
    if (error) throw new Error(error.message)
    return { session: toUserSession(data.session) }
  },

  async register(email: string, password: string, name?: string): Promise<AuthResult> {
    const client = requireSupabase()
    const { data, error } = await client.auth.signUp({
      email,
      password,
      options: { data: name ? { name } : undefined, emailRedirectTo: 'meetastro://auth/callback' },
    })
    if (error) throw new Error(error.message)
    return {
      session: toUserSession(data.session),
      message: data.session ? undefined : 'Vui lòng kiểm tra email để xác nhận tài khoản.',
    }
  },

  async forgotPassword(email: string): Promise<void> {
    const client = requireSupabase()
    const { error } = await client.auth.resetPasswordForEmail(email, {
      redirectTo: 'meetastro://auth/callback',
    })
    if (error) throw new Error(error.message)
  },

  async getOAuthUrl(provider: 'google', redirectTo: string): Promise<{ url: string }> {
    const client = requireSupabase()
    const { data, error } = await client.auth.signInWithOAuth({
      provider,
      options: { redirectTo, skipBrowserRedirect: true },
    })
    if (error) throw new Error(error.message)
    if (!data.url) throw new Error('Không tạo được Google OAuth URL.')
    return { url: data.url }
  },

  async setSession(accessToken: string, refreshToken: string): Promise<UserSession> {
    const client = requireSupabase()
    const { data, error } = await client.auth.setSession({
      access_token: accessToken,
      refresh_token: refreshToken,
    })
    if (error) throw new Error(error.message)
    const session = toUserSession(data.session)
    if (!session) throw new Error('Callback không tạo được phiên đăng nhập.')
    return session
  },

  async updatePassword(newPassword: string): Promise<void> {
    const client = requireSupabase()
    const { error } = await client.auth.updateUser({ password: newPassword })
    if (error) throw new Error(error.message)
  },

  async logout(): Promise<void> {
    const client = requireSupabase()
    const { error } = await client.auth.signOut()
    if (error) throw new Error(error.message)
  },

  async getSession(): Promise<UserSession | null> {
    const client = requireSupabase()
    const { data, error } = await client.auth.getSession()
    if (error) throw new Error(error.message)
    return toUserSession(data.session)
  },

  onAuthStateChange(callback: (session: UserSession | null) => void): () => void {
    const client = requireSupabase()
    const { data } = client.auth.onAuthStateChange((_event, session) => {
      callback(toUserSession(session))
    })
    return () => data.subscription.unsubscribe()
  },
}
