import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { TemplateVersionManager } from './TemplateVersionManager';
import { RiskPolicyManager } from './RiskPolicyManager';
import { AssetClassManager } from './AssetClassManager';
import { NavFeedManager } from './NavFeedManager';

export const AdminPage: React.FC<{ initialTab?: string }> = ({ initialTab = 'templates' }) => {
  const { token } = useAuth();
  const [activeTab, setActiveTab] = useState<'templates' | 'policies' | 'assets' | 'nav'>(
    initialTab === 'admin-policies'
      ? 'policies'
      : initialTab === 'admin-assets'
        ? 'assets'
        : initialTab === 'admin-nav'
          ? 'nav'
          : 'templates',
  );

  return (
    <div className="feature-page admin-page">
      <div className="page-header">
        <div>
          <h2 className="page-title">Platform Administration & Governance</h2>
          <p className="page-subtitle">
            Manage versioned investment templates, risk scoring questionnaires, asset classes, and daily market NAV operations.
          </p>
        </div>
      </div>

      <div className="tab-nav">
        <button
          type="button"
          className={`tab-btn ${activeTab === 'templates' ? 'tab-btn--active' : ''}`}
          onClick={() => setActiveTab('templates')}
          id="admin-tab-templates"
        >
          📑 Template Versions
        </button>
        <button
          type="button"
          className={`tab-btn ${activeTab === 'policies' ? 'tab-btn--active' : ''}`}
          onClick={() => setActiveTab('policies')}
          id="admin-tab-policies"
        >
          📜 Risk Policies
        </button>
        <button
          type="button"
          className={`tab-btn ${activeTab === 'assets' ? 'tab-btn--active' : ''}`}
          onClick={() => setActiveTab('assets')}
          id="admin-tab-assets"
        >
          🏷️ Asset Classes
        </button>
        <button
          type="button"
          className={`tab-btn ${activeTab === 'nav' ? 'tab-btn--active' : ''}`}
          onClick={() => setActiveTab('nav')}
          id="admin-tab-nav"
        >
          📈 NAV Feed Ops
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'templates' && <TemplateVersionManager token={token} />}
        {activeTab === 'policies' && <RiskPolicyManager token={token} />}
        {activeTab === 'assets' && <AssetClassManager token={token} />}
        {activeTab === 'nav' && <NavFeedManager token={token} />}
      </div>
    </div>
  );
};
