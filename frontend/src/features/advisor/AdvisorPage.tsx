import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import {
  listAdvisorCustomers,
  submitManualRecommendation,
  submitRiskOverride,
} from '../../api/advisorApi';
import type {
  AdvisorCustomerOut,
  ManualRecommendationIn,
  RiskOverrideIn,
} from '../../types/advisor';
import { CustomerList } from './CustomerList';
import { CustomerDetailModal } from './CustomerDetailModal';
import { RiskOverrideModal } from './RiskOverrideModal';
import { ManualRecommendationModal } from './ManualRecommendationModal';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { Alert } from '../../components/common/Alert';
import { StatCard } from '../../components/common/StatCard';

export const AdvisorPage: React.FC = () => {
  const { token, persona } = useAuth();
  const [customers, setCustomers] = useState<AdvisorCustomerOut[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedCustomerForDetail, setSelectedCustomerForDetail] = useState<string | null>(null);
  const [selectedCustomerForOverride, setSelectedCustomerForOverride] = useState<AdvisorCustomerOut | null>(null);
  const [selectedCustomerForManualRec, setSelectedCustomerForManualRec] = useState<AdvisorCustomerOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadCustomers = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const list = await listAdvisorCustomers(token);
      setCustomers(list);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load assigned customers.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCustomers();
  }, [token, persona]);

  const handleRiskOverrideSubmit = async (customerId: string, data: RiskOverrideIn) => {
    await submitRiskOverride(token, customerId, data);
    setSuccessMsg(`Risk band override recorded for client! Effective band is now ${data.new_band}.`);
    await loadCustomers();
  };

  const handleManualRecSubmit = async (customerId: string, data: ManualRecommendationIn) => {
    await submitManualRecommendation(token, customerId, data);
    setSuccessMsg('Manual recommendation recorded and published to client portfolio!');
    await loadCustomers();
  };

  if (isLoading) {
    return <LoadingSpinner message="Loading assigned client accounts..." />;
  }

  const totalClients = customers.length;
  const breachedClients = customers.filter((c) => c.portfolio_breached).length;
  const rebalanceOpenCount = customers.filter((c) => c.open_rebalance_id).length;

  return (
    <div className="feature-page advisor-page">
      <div className="page-header">
        <div>
          <h2 className="page-title">Advisor Workbench</h2>
          <p className="page-subtitle">
            Manage assigned client portfolios, monitor drift breaches, issue fiduciary risk overrides, and tailor custom allocations.
          </p>
        </div>
      </div>

      {error && <Alert type="error" title="Error" message={error} onClose={() => setError(null)} />}
      {successMsg && (
        <Alert type="success" title="Success" message={successMsg} onClose={() => setSuccessMsg(null)} />
      )}

      <div className="kpi-grid">
        <StatCard
          title="Assigned Clients"
          value={totalClients}
          subtitle="Directly managed retail accounts"
          variant="indigo"
          icon="👥"
        />

        <StatCard
          title="Drift Alerts"
          value={breachedClients}
          subtitle={breachedClients > 0 ? 'Clients requiring rebalance' : 'All portfolios within threshold'}
          variant={breachedClients > 0 ? 'rose' : 'emerald'}
          icon={breachedClients > 0 ? '⚠️' : '✅'}
        />

        <StatCard
          title="Active Proposals"
          value={rebalanceOpenCount}
          subtitle="Open rebalancing proposals"
          variant="amber"
          icon="⚖️"
        />
      </div>

      <CustomerList
        customers={customers}
        onSelectCustomer={(c) => setSelectedCustomerForDetail(c.customer_id)}
        onOpenRiskOverride={(c) => setSelectedCustomerForOverride(c)}
        onOpenManualRec={(c) => setSelectedCustomerForManualRec(c)}
      />

      <CustomerDetailModal
        customerId={selectedCustomerForDetail}
        token={token}
        onClose={() => setSelectedCustomerForDetail(null)}
      />

      {selectedCustomerForOverride && (
        <RiskOverrideModal
          customer={selectedCustomerForOverride}
          onClose={() => setSelectedCustomerForOverride(null)}
          onSubmit={handleRiskOverrideSubmit}
        />
      )}

      {selectedCustomerForManualRec && (
        <ManualRecommendationModal
          customer={selectedCustomerForManualRec}
          onClose={() => setSelectedCustomerForManualRec(null)}
          onSubmit={handleManualRecSubmit}
        />
      )}
    </div>
  );
};
