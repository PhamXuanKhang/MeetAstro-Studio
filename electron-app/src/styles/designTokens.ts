import type { CSSProperties } from 'react'

export const colors = {
  background: '#f6f5f4',
  surface: '#ffffff',
  text: '#1a1a1a',
  muted: '#5d5b54',
  primary: '#5645d4',
  success: '#1aae39',
  warning: '#dd5b00',
  danger: '#e03131',
  border: '#e5e3df',
  input: '#fafaf9',
}

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
}

export const radius = {
  sm: 6,
  md: 8,
  lg: 12,
  xl: 16,
}

export const shadows = {
  card: '0 4px 12px rgba(15, 15, 15, 0.08)',
}

export const inputStyle: CSSProperties = {
  width: '100%',
  padding: '10px 12px',
  border: `1px solid ${colors.border}`,
  borderRadius: radius.md,
  fontSize: 13,
  outline: 'none',
  background: colors.input,
  color: colors.text,
  boxSizing: 'border-box',
}

export const buttonPrimary: CSSProperties = {
  padding: '10px 16px',
  background: colors.primary,
  color: '#fff',
  border: 'none',
  borderRadius: radius.md,
  fontWeight: 700,
  fontSize: 14,
  cursor: 'pointer',
}

export const buttonSecondary: CSSProperties = {
  padding: '10px 16px',
  background: colors.surface,
  color: colors.text,
  border: `1px solid ${colors.border}`,
  borderRadius: radius.md,
  fontWeight: 600,
  fontSize: 13,
  cursor: 'pointer',
}

export const buttonDanger: CSSProperties = {
  ...buttonSecondary,
  color: colors.danger,
  border: '1px solid #f4b8b8',
}

export const buttonDisabled: CSSProperties = {
  background: colors.border,
  color: '#bbb8b1',
  border: `1px solid ${colors.border}`,
  cursor: 'not-allowed',
  opacity: 0.8,
}

export const alertSuccess: CSSProperties = {
  padding: '10px 14px',
  background: '#d9f3e1',
  border: '1px solid #b7e6c4',
  borderRadius: radius.md,
  fontSize: 13,
  color: '#0f6f25',
}

export const alertError: CSSProperties = {
  padding: '10px 14px',
  background: '#fde0ec',
  border: '1px solid #f5b8cf',
  borderRadius: radius.md,
  fontSize: 13,
  color: '#9f1d1d',
}

export const alertWarning: CSSProperties = {
  padding: '10px 14px',
  background: '#fef7d6',
  border: '1px solid #f5d75e',
  borderRadius: radius.md,
  fontSize: 12,
  color: '#793400',
}
