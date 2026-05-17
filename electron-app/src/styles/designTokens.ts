import type { CSSProperties } from 'react'

export const cssVar = (name: string) => `var(${name})`

export const colors = {
  background: cssVar('--color-bg'),
  backgroundAlt: cssVar('--color-bg-alt'),
  surface: cssVar('--color-surface'),
  surface2: cssVar('--color-surface-2'),
  surface3: cssVar('--color-surface-3'),
  text: cssVar('--color-text-main'),
  muted: cssVar('--color-text-muted'),
  subtle: cssVar('--color-text-subtle'),
  primary: cssVar('--color-primary'),
  primaryHover: cssVar('--color-primary-hover'),
  success: cssVar('--color-success'),
  warning: cssVar('--color-warning'),
  danger: cssVar('--color-danger'),
  info: cssVar('--color-info'),
  border: cssVar('--color-border'),
  borderSubtle: cssVar('--color-border-subtle'),
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
  md: cssVar('--radius-brand'),
  lg: cssVar('--radius-brand-lg'),
  chip: cssVar('--radius-chip'),
}

export const shadows = {
  soft: cssVar('--shadow-soft'),
  card: cssVar('--shadow-soft'),
  cardHover: cssVar('--shadow-card-hover'),
  elev: cssVar('--shadow-elev'),
  focus: cssVar('--shadow-focus'),
}

export const inputStyle: CSSProperties = {
  width: '100%',
  padding: '10px 12px',
  border: `1px solid ${colors.border}`,
  borderRadius: radius.md,
  fontSize: 13,
  outline: 'none',
  background: colors.surface,
  color: colors.text,
  boxSizing: 'border-box',
}

export const buttonPrimary: CSSProperties = {
  padding: '10px 16px',
  background: colors.primary,
  color: 'white',
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
  border: `1px solid ${colors.border}`,
}

export const buttonDisabled: CSSProperties = {
  background: colors.surface3,
  color: colors.subtle,
  border: `1px solid ${colors.border}`,
  cursor: 'not-allowed',
  opacity: 0.5,
}

export const alertSuccess: CSSProperties = {
  padding: '10px 14px',
  background: 'color-mix(in srgb, var(--color-success) 10%, transparent)',
  border: '1px solid color-mix(in srgb, var(--color-success) 30%, transparent)',
  borderRadius: radius.md,
  fontSize: 13,
  color: colors.success,
}

export const alertError: CSSProperties = {
  padding: '10px 14px',
  background: 'color-mix(in srgb, var(--color-danger) 10%, transparent)',
  border: '1px solid color-mix(in srgb, var(--color-danger) 30%, transparent)',
  borderRadius: radius.md,
  fontSize: 13,
  color: colors.danger,
}

export const alertWarning: CSSProperties = {
  padding: '10px 14px',
  background: 'color-mix(in srgb, var(--color-warning) 10%, transparent)',
  border: '1px solid color-mix(in srgb, var(--color-warning) 30%, transparent)',
  borderRadius: radius.md,
  fontSize: 12,
  color: colors.warning,
}
