import React from 'react';

interface LoadingSpinnerProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  message = 'Loading data...',
  size = 'md',
  className = '',
}) => {
  return (
    <div className={`loading-container ${className}`} role="status" aria-live="polite">
      <div className={`spinner spinner--${size}`} />
      {message && <p className="loading-message">{message}</p>}
    </div>
  );
};
