export type DeepLinkResult = {
  type: 'oauth' | 'email_verification' | 'password_recovery' | 'unknown'
  accessToken?: string
  refreshToken?: string
  error?: string
  errorDescription?: string
}

function readParams(url: URL): URLSearchParams {
  const params = new URLSearchParams(url.search)
  const fragment = url.hash.startsWith('#') ? url.hash.slice(1) : url.hash
  const fragmentParams = new URLSearchParams(fragment)
  fragmentParams.forEach((value, key) => params.set(key, value))
  return params
}

export function parseAuthDeepLink(rawUrl: string): DeepLinkResult {
  try {
    const url = new URL(rawUrl)
    if (url.protocol !== 'meetastro:' || url.hostname !== 'auth') {
      return { type: 'unknown' }
    }

    const params = readParams(url)
    const error = params.get('error') ?? undefined
    const errorDescription = params.get('error_description') ?? undefined
    if (error || errorDescription) {
      return { type: 'unknown', error, errorDescription }
    }

    const supabaseType = params.get('type')
    const accessToken = params.get('access_token') ?? undefined
    const refreshToken = params.get('refresh_token') ?? undefined

    if (supabaseType === 'recovery') {
      return { type: 'password_recovery', accessToken, refreshToken }
    }
    if (supabaseType === 'signup') {
      return { type: 'email_verification', accessToken, refreshToken }
    }
    if (accessToken && refreshToken) {
      return { type: 'oauth', accessToken, refreshToken }
    }

    return { type: 'unknown' }
  } catch {
    return { type: 'unknown' }
  }
}
