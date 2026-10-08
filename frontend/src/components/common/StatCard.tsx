import React from 'react';

interface StatCardProps {
  title: string;
  value: React.ReactNode;
  subtitle?: React.ReactNode;
  icon?: React.ReactNode;
  variant?: 'emerald' | 'indigo' | 'amber' | 'rose' | 'slate';
  trend?: {
    label: string;
    isPositive?: boolean;
  };
  className?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  variant = 'indigo',
  trend,
  className = '',
}) => {
  return (
    <div className={`stat-card stat-card--${variant} ${className}`}>
      <div className="stat-card__header">
        <span className="stat-card__title">{title}</span>
        {icon && <div className="stat-card__icon">{icon}</div>}
      </div>
      <div className="stat-card__value">{value}</div>
      {(subtitle || trend) && (
        <div className="stat-card__footer">
          {trend && (
            <span className={`stat-card__trend ${trend.isPositive ? 'trend--up' : 'trend--down'}`}>
              {trend.isPositive ? '▲ ' : '▼ '}
              {trend.label}
            </span>
          )}
          {subtitle && <span className="stat-card__subtitle">{subtitle}</span>}
        </div>
      )}
    </div>
  );
};
