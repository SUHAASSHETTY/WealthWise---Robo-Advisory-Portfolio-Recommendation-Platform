import React from 'react';
import { RoleSwitcher } from './RoleSwitcher';
import type { HealthStatus } from '../../types/health';

interface NavbarProps {
  health: { kind: 'loading' } | { kind: 'loaded'; health: HealthStatus } | { kind: 'error' };
  onToggleSidebar?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ health, onToggleSidebar }) => {

  const healthBadge =
    health.kind === 'loading'
      ? { text: 'API Checking...', cls: 'badge--neutral' }
      : health.kind === 'error'
        ? { text: 'API Offline', cls: 'badge--danger' }
        : health.health.status === 'ok'
          ? { text: 'API Healthy', cls: 'badge--success' }
          : { text: 'API Degraded', cls: 'badge--warning' };

  return (
    <header className="navbar">
      <div className="navbar__left">
        {onToggleSidebar && (
          <button
            type="button"
            className="navbar__menu-toggle"
            id="menu-toggle-btn"
            onClick={onToggleSidebar}
            aria-label="Toggle navigation menu"
          >
            ☰
          </button>
        )}
        <div className="navbar__brand">
          <div className="navbar__logo">
            <span>W</span>
          </div>
          <div className="navbar__title-group">
            <h1 className="navbar__title">WealthWise</h1>
            <span className="navbar__subtitle">Robo-Advisory Platform</span>
          </div>
        </div>
      </div>

      <div className="navbar__right">
        <div className="navbar__health">
          <span className={`badge ${healthBadge.cls}`} role="status">
            <span className="status-indicator" />
            {healthBadge.text}
          </span>
        </div>
        <RoleSwitcher />
      </div>
    </header>
  );
};
