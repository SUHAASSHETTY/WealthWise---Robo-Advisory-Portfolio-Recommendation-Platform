import React from 'react';

interface FormattedMoneyProps {
  value: string | number | null | undefined;
  currency?: string;
  className?: string;
}

export const FormattedMoney: React.FC<FormattedMoneyProps> = ({
  value,
  currency = '$',
  className = '',
}) => {
  if (value === null || value === undefined || value === '') {
    return <span className={`money-text money-text--empty ${className}`}>—</span>;
  }

  // Parse for display-only formatting per NFR-01 (no math performed)
  const num = typeof value === 'number' ? value : parseFloat(value);
  if (isNaN(num)) {
    return <span className={`money-text ${className}`}>{String(value)}</span>;
  }

  const formatted = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);

  return (
    <span className={`money-text ${className}`}>
      <span className="money-currency">{currency}</span>
      <span className="money-val">{formatted}</span>
    </span>
  );
};
