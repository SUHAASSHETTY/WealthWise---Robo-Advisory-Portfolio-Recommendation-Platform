import React from 'react';

interface FormattedPercentProps {
  value: string | number | null | undefined;
  className?: string;
}

export const FormattedPercent: React.FC<FormattedPercentProps> = ({ value, className = '' }) => {
  if (value === null || value === undefined || value === '') {
    return <span className={`pct-text pct-text--empty ${className}`}>—</span>;
  }

  const num = typeof value === 'number' ? value : parseFloat(value);
  if (isNaN(num)) {
    return <span className={`pct-text ${className}`}>{String(value)}%</span>;
  }

  const formatted = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);

  return (
    <span className={`pct-text ${className}`}>
      <span className="pct-val">{formatted}</span>
      <span className="pct-sign">%</span>
    </span>
  );
};
