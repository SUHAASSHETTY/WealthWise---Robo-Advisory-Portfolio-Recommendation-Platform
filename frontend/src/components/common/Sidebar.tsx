import React from 'react';
import { useAuth } from '../../context/AuthContext';

export type NavTabId =
  | 'risk-profile'
  | 'goals'
  | 'recommendation'
  | 'holdings'
  | 'rebalancing'
  | 'advisor'
  | 'admin-templates'
  | 'admin-policies'
  | 'admin-assets'
  | 'admin-nav';

interface SidebarProps {
  activeTab: NavTabId;
  onSelectTab: (tab: NavTabId) => void;
  isOpen?: boolean;
  onClose?: () => void;
}

interface NavItem {
  id: NavTabId;
  label: string;
  icon: string;
  badge?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  isOpen = false,
  onClose,
}) => {
  const { role } = useAuth();

  const customerNav: NavItem[] = [
    { id: 'risk-profile', label: 'Risk Profile', icon: '🎯' },
    { id: 'goals', label: 'Goals Tracker', icon: '🏆' },
    { id: 'recommendation', label: 'Recommendation', icon: '📊' },
    { id: 'holdings', label: 'Holdings & Drift', icon: '💼' },
    { id: 'rebalancing', label: 'Rebalancing', icon: '⚖️' },
  ];

  const advisorNav: NavItem[] = [
    { id: 'advisor', label: 'Advisor Workbench', icon: '👥' },
  ];

  const adminNav: NavItem[] = [
    { id: 'admin-templates', label: 'Template Versions', icon: '📑' },
    { id: 'admin-policies', label: 'Risk Policies', icon: '📜' },
    { id: 'admin-assets', label: 'Asset Classes', icon: '🏷️' },
    { id: 'admin-nav', label: 'NAV Feed Ops', icon: '📈' },
  ];

  const navItems = role === 'CUSTOMER' ? customerNav : role === 'ADVISOR' ? advisorNav : adminNav;

  return (
    <>
      {isOpen && <div className="sidebar-backdrop" onClick={onClose} />}
      <aside className={`sidebar ${isOpen ? 'sidebar--open' : ''}`}>
        <div className="sidebar__section-title">
          {role === 'CUSTOMER' ? 'Client Services' : role === 'ADVISOR' ? 'Advisor Tools' : 'Administration'}
        </div>
        <nav className="sidebar__nav" aria-label="Main Navigation">
          <ul className="sidebar__list">
            {navItems.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <li key={item.id} className="sidebar__item">
                  <button
                    type="button"
                    className={`sidebar__link ${isActive ? 'sidebar__link--active' : ''}`}
                    onClick={() => {
                      onSelectTab(item.id);
                      if (onClose) onClose();
                    }}
                    aria-current={isActive ? 'page' : undefined}
                  >
                    <span className="sidebar__icon">{item.icon}</span>
                    <span className="sidebar__label">{item.label}</span>
                    {item.badge && <span className="sidebar__badge">{item.badge}</span>}
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="sidebar__footer">
          <div className="sidebar__security-badge">
            <span className="shield-icon">🛡️</span>
            <div className="security-text">
              <span className="sec-title">Fixed-Point Decimal</span>
              <span className="sec-sub">NFR-01 Strict Precision</span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
