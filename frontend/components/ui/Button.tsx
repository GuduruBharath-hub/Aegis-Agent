'use client';

import React from 'react';
import { cn } from '@/lib/utils';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'success';
type Size = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const variantStyles: Record<Variant, string> = {
  primary: `
    background: linear-gradient(135deg, rgba(0,212,255,0.15), rgba(0,212,255,0.08));
    border: 1px solid rgba(0,212,255,0.4);
    color: #00d4ff;
  `,
  secondary: `
    background: rgba(17, 34, 64, 0.8);
    border: 1px solid rgba(0,212,255,0.15);
    color: rgba(200,220,255,0.8);
  `,
  ghost: `
    background: transparent;
    border: 1px solid transparent;
    color: rgba(200,220,255,0.65);
  `,
  danger: `
    background: rgba(255, 61, 113, 0.12);
    border: 1px solid rgba(255, 61, 113, 0.35);
    color: #ff4d6d;
  `,
  success: `
    background: rgba(0, 230, 118, 0.1);
    border: 1px solid rgba(0, 230, 118, 0.3);
    color: #00e676;
  `,
};

const sizeStyles: Record<Size, React.CSSProperties> = {
  sm: { padding: '4px 12px', fontSize: '0.8rem', borderRadius: '6px', height: '28px' },
  md: { padding: '7px 18px', fontSize: '0.875rem', borderRadius: '8px', height: '36px' },
  lg: { padding: '10px 24px', fontSize: '1rem', borderRadius: '10px', height: '44px' },
};

export const Button: React.FC<ButtonProps> = ({
  variant = 'secondary',
  size = 'md',
  loading = false,
  leftIcon,
  rightIcon,
  children,
  className,
  disabled,
  style,
  ...props
}) => {
  const isDisabled = disabled || loading;

  return (
    <button
      {...props}
      disabled={isDisabled}
      className={cn('aegis-btn', className)}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        fontFamily: 'Inter, sans-serif',
        fontWeight: 500,
        cursor: isDisabled ? 'not-allowed' : 'pointer',
        opacity: isDisabled ? 0.55 : 1,
        transition: 'all 0.2s ease',
        outline: 'none',
        whiteSpace: 'nowrap',
        ...sizeStyles[size],
        ...style,
      }}
    >
      <style>{`
        .aegis-btn[data-variant="primary"]:hover:not(:disabled) {
          box-shadow: 0 0 16px rgba(0,212,255,0.35);
          border-color: rgba(0,212,255,0.7) !important;
        }
        .aegis-btn[data-variant="danger"]:hover:not(:disabled) {
          box-shadow: 0 0 16px rgba(255,61,113,0.3);
        }
        .aegis-btn[data-variant="success"]:hover:not(:disabled) {
          box-shadow: 0 0 16px rgba(0,230,118,0.25);
        }
      `}</style>
      <span
        data-variant={variant}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          width: '100%',
          height: '100%',
        }}
      >
        {loading ? (
          <span
            style={{
              width: '14px',
              height: '14px',
              border: '2px solid currentColor',
              borderTopColor: 'transparent',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite',
              display: 'inline-block',
            }}
          />
        ) : leftIcon}
        {children}
        {!loading && rightIcon}
      </span>
    </button>
  );
};

// Create a styled version that injects inline CSS
const StyledButton: React.FC<ButtonProps> = (props) => {
  const { variant = 'secondary', size = 'md', style, ...rest } = props;
  const [variantKey] = Object.entries({
    primary: 'primary',
    secondary: 'secondary',
    ghost: 'ghost',
    danger: 'danger',
    success: 'success',
  }).find(([k]) => k === variant) ?? ['secondary'];

  // Parse CSS string to partial style
  const inlineVariant: React.CSSProperties = {};
  variantStyles[variantKey as Variant]
    .split(';')
    .map((s) => s.trim())
    .filter(Boolean)
    .forEach((rule) => {
      const [prop, val] = rule.split(':').map((s) => s.trim());
      if (prop && val) {
        const camel = prop.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
        (inlineVariant as Record<string, string>)[camel] = val;
      }
    });

  return <Button {...rest} variant={variant} size={size} style={{ ...inlineVariant, ...style }} />;
};

export default StyledButton;
