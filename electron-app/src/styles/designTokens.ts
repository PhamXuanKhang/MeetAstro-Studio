import type { CSSProperties } from 'react'

export const colors = {
  background: '#f8fafc',
  surface: '#ffffff',
  text: '#0f172a',
  muted: '#64748b',
  primary: '#0ea5e9',
  success: '#16a34a',
  warning: '#ca8a04',
  danger: '#dc2626',
  border: '#e2e8f0',
  input: '#f8fafc',
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
  card: '0 4px 24px rgba(15, 23, 42, 0.06)',
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
  border: '1px solid #fca5a5',
}

export const buttonDisabled: CSSProperties = {
  background: '#f1f5f9',
  color: '#94a3b8',
  border: `1px solid ${colors.border}`,
  cursor: 'not-allowed',
  opacity: 0.8,
}

export const alertSuccess: CSSProperties = {
  padding: '10px 14px',
  background: '#dcfce7',
  border: '1px solid #bbf7d0',
  borderRadius: radius.md,
  fontSize: 13,
  color: '#166534',
}

export const alertError: CSSProperties = {
  padding: '10px 14px',
  background: '#fee2e2',
  border: '1px solid #fecaca',
  borderRadius: radius.md,
  fontSize: 13,
  color: '#991b1b',
}

export const alertWarning: CSSProperties = {
  padding: '10px 14px',
  background: '#fef9c3',
  border: '1px solid #fde68a',
  borderRadius: radius.md,
  fontSize: 12,
  color: '#713f12',
}
