import { useEffect, useState } from 'react';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { fetchHealth } from '../api/client';
import type { HealthStatus } from '../types/health';
import { Navbar } from '../components/common/Navbar';
import { Sidebar, type NavTabId } from '../components/common/Sidebar';
import { RiskProfilePage } from '../features/risk-profile/RiskProfilePage';
import { GoalsPage } from '../features/goals/GoalsPage';
import { RecommendationPage } from '../features/recommendation/RecommendationPage';
import { HoldingsPage } from '../features/holdings/HoldingsPage';
import { RebalancingPage } from '../features/rebalancing/RebalancingPage';
import { AdvisorPage } from '../features/advisor/AdvisorPage';
import { AdminPage } from '../features/admin/AdminPage';

type HealthState = { kind: 'loading' } | { kind: 'loaded'; health: HealthStatus } | { kind: 'error' };

function MainShell() {
  const { role } = useAuth();
  const [health, setHealth] = useState<HealthState>({ kind: 'loading' });
  const [activeTab, setActiveTab] = useState<NavTabId>('risk-profile');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  useEffect(() => {
    fetchHealth()
      .then((res) => setHealth({ kind: 'loaded', health: res }))
      .catch(() => setHealth({ kind: 'error' }));
  }, []);

  // Synchronize default tab on role changes
  useEffect(() => {
    if (role === 'CUSTOMER') {
      setActiveTab((prev) =>
        ['risk-profile', 'goals', 'recommendation', 'holdings', 'rebalancing'].includes(prev)
          ? prev
          : 'risk-profile',
      );
    } else if (role === 'ADVISOR') {
      setActiveTab('advisor');
    } else if (role === 'ADMIN') {
      setActiveTab((prev) =>
        ['admin-templates', 'admin-policies', 'admin-assets', 'admin-nav'].includes(prev)
          ? prev
          : 'admin-templates',
      );
    }
  }, [role]);

  return (
    <div className="app-layout">
      <Navbar health={health} onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)} />
      <div className="app-body">
        <Sidebar
          activeTab={activeTab}
          onSelectTab={setActiveTab}
          isOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
        />
        <main className="main-content" id="main-content-region">
          {role === 'CUSTOMER' && activeTab === 'risk-profile' && <RiskProfilePage />}
          {role === 'CUSTOMER' && activeTab === 'goals' && <GoalsPage />}
          {role === 'CUSTOMER' && activeTab === 'recommendation' && <RecommendationPage />}
          {role === 'CUSTOMER' && activeTab === 'holdings' && (
            <HoldingsPage onNavigateToRebalancing={() => setActiveTab('rebalancing')} />
          )}
          {role === 'CUSTOMER' && activeTab === 'rebalancing' && <RebalancingPage />}
          {role === 'ADVISOR' && <AdvisorPage />}
          {role === 'ADMIN' && <AdminPage initialTab={activeTab} />}
        </main>
      </div>
    </div>
  );
}

export function App() {
  return (
    <AuthProvider>
      <MainShell />
    </AuthProvider>
  );
}
