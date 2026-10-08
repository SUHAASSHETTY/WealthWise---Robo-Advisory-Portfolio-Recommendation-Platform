import React from 'react';

interface AlertProps {
  type?: 'info' | 'success' | 'warning' | 'error';
  title?: string;
  message?: string;
  children?: React.ReactNode;
  onClose?: () => void;
  className?: string;
}

export const Alert: React.FC<AlertProps> = ({
  type = 'info',
  title,
  message,
  children,
  onClose,
  className = '',
}) => {
  return (
    <div className={`alert alert--${type} ${className}`} role="alert">
      <div className="alert__content">
        {title && <h4 className="alert__title">{title}</h4>}
        {message && <p className="alert__message">{message}</p>}
        {children}
      </div>
      {onClose && (
        <button
          type="button"
          className="alert__close-btn"
          onClick={onClose}
          aria-label="Close alert"
        >
          ✕
        </button>
      )}
    </div>
  );
};
