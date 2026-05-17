import type { ButtonHTMLAttributes, CSSProperties, HTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react'

const mix = (token: string, amount: number) => `color-mix(in srgb, var(${token}) ${amount}%, transparent)`

export function Icon({ name, fill = false, size = 18, style }: { name: string; fill?: boolean; size?: number; style?: CSSProperties }) {
  return (
    <span
      className="material-symbols-outlined"
      style={{
        fontSize: size,
        lineHeight: 1,
        fontVariationSettings: `'FILL' ${fill ? 1 : 0}, 'wght' 400, 'GRAD' 0, 'opsz' ${size}`,
        ...style,
      }}
      aria-hidden="true"
    >
      {name}
    </span>
  )
}

type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success'
type ButtonSize = 'sm' | 'md' | 'lg'

const buttonSizeStyles: Record<ButtonSize, CSSProperties> = {
  sm: { height: 28, padding: '0 12px', fontSize: 12, borderRadius: 6 },
  md: { height: 36, padding: '0 16px', fontSize: 14, borderRadius: 'var(--radius-brand)' },
  lg: { height: 44, padding: '0 24px', fontSize: 14, borderRadius: 'var(--radius-brand)' },
}

const buttonVariantStyles: Record<ButtonVariant, CSSProperties> = {
  primary: { background: 'var(--color-primary)', color: 'white', border: '1px solid var(--color-primary)' },
  secondary: { background: 'var(--color-surface)', color: 'var(--color-text-main)', border: '1px solid var(--color-border)' },
  outline: { background: 'transparent', color: 'var(--color-text-main)', border: '1px solid var(--color-border)' },
  ghost: { background: 'transparent', color: 'var(--color-text-muted)', border: '1px solid transparent' },
  danger: { background: 'var(--color-danger)', color: 'white', border: '1px solid var(--color-danger)' },
  success: { background: 'var(--color-success)', color: 'white', border: '1px solid var(--color-success)' },
}

export function Button({
  variant = 'secondary',
  size = 'md',
  style,
  disabled,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; size?: ButtonSize }) {
  return (
    <button
      {...props}
      disabled={disabled}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        fontWeight: 700,
        cursor: disabled ? 'not-allowed' : 'pointer',
        transition: 'background 150ms ease-out, border-color 150ms ease-out, color 150ms ease-out, opacity 150ms ease-out',
        opacity: disabled ? 0.5 : 1,
        ...buttonSizeStyles[size],
        ...buttonVariantStyles[variant],
        ...style,
      }}
    >
      {children}
    </button>
  )
}

export function Card({ children, style, hover = false, ...props }: HTMLAttributes<HTMLDivElement> & { hover?: boolean }) {
  return (
    <div
      {...props}
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border-subtle)',
        borderRadius: 'var(--radius-brand-lg)',
        boxShadow: 'var(--shadow-soft)',
        transition: hover ? 'border-color 150ms ease-out, box-shadow 150ms ease-out' : undefined,
        ...style,
      }}
    >
      {children}
    </div>
  )
}

export function CardSection({ children, style, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      {...props}
      style={{
        padding: 16,
        borderRadius: 'var(--radius-brand)',
        background: 'var(--color-bg)',
        border: '1px solid var(--color-border-subtle)',
        ...style,
      }}
    >
      {children}
    </div>
  )
}

export function CardRow({ children, style, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      {...props}
      style={{
        padding: '12px 0',
        borderBottom: '1px solid var(--color-border-subtle)',
        ...style,
      }}
    >
      {children}
    </div>
  )
}

type BadgeVariant = 'default' | 'primary' | 'success' | 'warning' | 'error' | 'info'
type BadgeSize = 'sm' | 'md' | 'lg'

const badgeStyles: Record<BadgeVariant, CSSProperties> = {
  default: { background: 'var(--color-surface-2)', color: 'var(--color-text-muted)', border: '1px solid transparent' },
  primary: { background: mix('--color-primary', 10), color: 'var(--color-primary)', border: `1px solid ${mix('--color-primary', 20)}` },
  success: { background: mix('--color-success', 10), color: 'var(--color-success)', border: '1px solid transparent' },
  warning: { background: mix('--color-warning', 10), color: 'var(--color-warning)', border: '1px solid transparent' },
  error: { background: mix('--color-danger', 10), color: 'var(--color-danger)', border: '1px solid transparent' },
  info: { background: mix('--color-info', 10), color: 'var(--color-info)', border: '1px solid transparent' },
}

const badgeSizeStyles: Record<BadgeSize, CSSProperties> = {
  sm: { padding: '2px 8px', fontSize: 10 },
  md: { padding: '4px 10px', fontSize: 12 },
  lg: { padding: '6px 12px', fontSize: 14 },
}

export function Badge({ variant = 'default', size = 'md', dot = false, children, style, ...props }: HTMLAttributes<HTMLSpanElement> & { variant?: BadgeVariant; size?: BadgeSize; dot?: boolean }) {
  return (
    <span
      {...props}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        borderRadius: 'var(--radius-chip)',
        fontWeight: 700,
        lineHeight: 1.2,
        ...badgeStyles[variant],
        ...badgeSizeStyles[size],
        ...style,
      }}
    >
      {dot && <span style={{ width: 6, height: 6, borderRadius: 999, background: 'currentColor' }} />}
      {children}
    </span>
  )
}

export function Field({ label, hint, error, required, children }: { label?: string; hint?: string; error?: string; required?: boolean; children: ReactNode }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {label && (
        <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text-main)' }}>
          {label}{required && <span style={{ color: 'var(--color-danger)', marginLeft: 4 }}>*</span>}
        </span>
      )}
      {children}
      {error && <span style={{ fontSize: 12, color: 'var(--color-danger)' }}>{error}</span>}
      {!error && hint && <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>{hint}</span>}
    </label>
  )
}

export function Input({ style, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      style={{
        width: '100%',
        padding: '10px 12px',
        borderRadius: 'var(--radius-brand)',
        border: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
        color: 'var(--color-text-main)',
        outline: 'none',
        fontSize: 'max(16px, 0.875rem)',
        ...style,
      }}
    />
  )
}

export function Select({ style, children, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      style={{
        width: '100%',
        padding: '10px 40px 10px 12px',
        borderRadius: 'var(--radius-brand)',
        border: '1px solid var(--color-border)',
        background: 'var(--color-surface)',
        color: 'var(--color-text-main)',
        outline: 'none',
        fontSize: 14,
        appearance: 'none',
        ...style,
      }}
    >
      {children}
    </select>
  )
}

export function Toggle({ checked, disabled, onClick }: { checked: boolean; disabled?: boolean; onClick?: () => void }) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      style={{
        width: 44,
        height: 24,
        borderRadius: 999,
        padding: 2,
        background: checked ? 'var(--color-primary)' : 'var(--color-surface-3)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        transition: 'background 200ms ease-in-out',
      }}
    >
      <span
        style={{
          display: 'block',
          width: 20,
          height: 20,
          borderRadius: 999,
          background: 'white',
          boxShadow: 'var(--shadow-soft)',
          transform: checked ? 'translateX(20px)' : 'translateX(0)',
          transition: 'transform 200ms ease-in-out',
        }}
      />
    </button>
  )
}

export function Modal({ open, title, children, footer, onClose }: { open: boolean; title?: string; children: ReactNode; footer?: ReactNode; onClose?: () => void }) {
  if (!open) return null
  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
      <div onClick={onClose} style={{ position: 'absolute', inset: 0, background: 'rgba(0, 0, 0, 0.5)', backdropFilter: 'blur(2px)' }} />
      <Card style={{ position: 'relative', zIndex: 1, width: '100%', maxWidth: 520, boxShadow: 'var(--shadow-elev)' }}>
        {title && <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--color-border-subtle)', fontWeight: 700 }}>{title}</div>}
        <div className="custom-scrollbar" style={{ padding: 24, maxHeight: 'calc(85vh - 100px)', overflowY: 'auto' }}>{children}</div>
        {footer && <div style={{ padding: 24, borderTop: '1px solid var(--color-border-subtle)', display: 'flex', justifyContent: 'flex-end', gap: 12 }}>{footer}</div>}
      </Card>
    </div>
  )
}

export function Toast({ type = 'info', title, message }: { type?: BadgeVariant; title: string; message?: string }) {
  const variant = type === 'error' ? 'error' : type === 'success' ? 'success' : type === 'warning' ? 'warning' : 'info'
  return (
    <div style={{ borderRadius: 8, border: badgeStyles[variant].border, background: badgeStyles[variant].background, color: badgeStyles[variant].color, padding: '8px 12px', boxShadow: 'var(--shadow-elev)' }}>
      <div style={{ fontSize: 12, fontWeight: 700 }}>{title}</div>
      {message && <div style={{ fontSize: 12, marginTop: 2, whiteSpace: 'pre-wrap' }}>{message}</div>}
    </div>
  )
}

export function EmptyState({ icon, title, description, action }: { icon: string; title: string; description?: string; action?: ReactNode }) {
  return (
    <div style={{ minHeight: 220, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: '40px 24px', color: 'var(--color-text-muted)' }}>
      <Icon name={icon} size={40} />
      <div style={{ marginTop: 12, fontSize: 14, fontWeight: 700, color: 'var(--color-text-main)' }}>{title}</div>
      {description && <div style={{ marginTop: 6, fontSize: 14, maxWidth: 360 }}>{description}</div>}
      {action && <div style={{ marginTop: 16 }}>{action}</div>}
    </div>
  )
}

