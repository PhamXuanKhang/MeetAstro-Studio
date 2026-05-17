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
  try {
    // Chromium does not parse authority for custom protocols — check by string prefix instead
    if (!rawUrl.startsWith('meetastro://auth')) {
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

    if (supabaseType === 'recovery') {
      return { type: 'password_recovery', code, accessToken, refreshToken }
    }
    if (supabaseType === 'signup') {
      return { type: 'email_verification', code, accessToken, refreshToken }
    }
    if (code) {
      return { type: 'oauth_pkce', code }
    }
    if (accessToken && refreshToken) {
      return { type: 'oauth', accessToken, refreshToken }
    }

    return { type: 'unknown' }
  } catch (e) {
    console.error('[auth] parseAuthDeepLink error:', e)
    return { type: 'unknown' }
  }
}
