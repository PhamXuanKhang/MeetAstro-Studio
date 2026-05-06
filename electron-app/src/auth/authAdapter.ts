export interface UserSession {
  userId: string
  email: string
  name?: string | null
  accessToken?: string | null
}

export interface AuthResult {
  session: UserSession | null
  message?: string
}

export interface AuthAdapter {
  login: (email: string, password: string) => Promise<AuthResult>
  register: (email: string, password: string, name?: string) => Promise<AuthResult>
  forgotPassword: (email: string) => Promise<void>
  logout: () => Promise<void>
  getSession: () => Promise<UserSession | null>
  onAuthStateChange: (callback: (session: UserSession | null) => void) => () => void
}
