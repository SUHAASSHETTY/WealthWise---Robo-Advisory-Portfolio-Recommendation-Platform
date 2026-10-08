import React from 'react';

export type BadgeVariant =
  | 'conservative'
  | 'moderate'
  | 'aggressive'
  | 'breached'
  | 'balanced'
  | 'buy'
  | 'sell'
  | 'hold'
  | 'achieved'
  | 'in_progress'
  | 'draft'
  | 'published'
  | 'archived'
  | 'info'
  | 'warning'
  | 'success'
  | 'danger'
  | 'neutral';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  icon?: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'md',
  className = '',
  icon,
}) => {
  return (
    <span className={`badge badge--${variant} badge--${size} ${className}`}>
      {icon && <span className="badge__icon">{icon}</span>}
      <span className="badge__label">{children}</span>
    </span>
  );
};
