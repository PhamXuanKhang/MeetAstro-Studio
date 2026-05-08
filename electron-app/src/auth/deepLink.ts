export type DeepLinkResult = {
  type: 'oauth' | 'oauth_pkce' | 'email_verification' | 'password_recovery' | 'unknown'
  accessToken?: string
  refreshToken?: string
  code?: string
  error?: string
  errorDescription?: string
}

function readParams(url: URL): URLSearchParams {
  // Load fragment first (tokens/code are usually only in fragment)
  const fragment = url.hash.startsWith('#') ? url.hash.slice(1) : url.hash
  const params = new URLSearchParams(fragment)
  // Search params override fragment — error_description is single-encoded in search
  // but double-encoded in fragment, so search takes precedence
  new URLSearchParams(url.search).forEach((value, key) => params.set(key, value))
  return params
}

export function parseAuthDeepLink(rawUrl: string): DeepLinkResult {
  console.log('[auth] parseAuthDeepLink input:', rawUrl)
  try {
    // Chromium does not parse authority for custom protocols — check by string prefix instead
    if (!rawUrl.startsWith('meetastro://auth')) {
      console.log('[auth] parseAuthDeepLink: not a meetastro://auth URL')
      return { type: 'unknown' }
    }
    const url = new URL(rawUrl)

    const params = readParams(url)
    const error = params.get('error') ?? undefined
    const errorDescription = params.get('error_description') ?? undefined
    if (error || errorDescription) {
      return { type: 'unknown', error, errorDescription }
    }

    const supabaseType = params.get('type')
    const accessToken = params.get('access_token') ?? undefined
    const refreshToken = params.get('refresh_token') ?? undefined

    const code = params.get('code') ?? undefined

    console.log('[auth] parseAuthDeepLink params — type:', supabaseType, 'code:', code ? 'present' : 'none', 'accessToken:', accessToken ? 'present' : 'none')

    if (supabaseType === 'recovery') {
      const r = { type: 'password_recovery' as const, code, accessToken, refreshToken }
      console.log('[auth] parseAuthDeepLink →', r.type)
      return r
    }
    if (supabaseType === 'signup') {
      const r = { type: 'email_verification' as const, code, accessToken, refreshToken }
      console.log('[auth] parseAuthDeepLink →', r.type)
      return r
    }
    if (code) {
      console.log('[auth] parseAuthDeepLink → oauth_pkce')
      return { type: 'oauth_pkce', code }
    }
    if (accessToken && refreshToken) {
      console.log('[auth] parseAuthDeepLink → oauth (implicit)')
      return { type: 'oauth', accessToken, refreshToken }
    }

    console.log('[auth] parseAuthDeepLink: unknown — params were', { supabaseType: params.get('type'), hasCode: !!params.get('code'), hasToken: !!params.get('access_token') })
    return { type: 'unknown' }
  } catch (e) {
    console.error('[auth] parseAuthDeepLink error:', e)
    return { type: 'unknown' }
  }
}
