import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { getHoldings } from '../../api/holdingsApi';
import type { HoldingsResponse } from '../../types/holdings';
import { HoldingsTable } from './HoldingsTable';
import { StatCard } from '../../components/common/StatCard';
import { FormattedMoney } from '../../components/common/FormattedMoney';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { Alert } from '../../components/common/Alert';
import { Badge } from '../../components/common/Badge';

export const HoldingsPage: React.FC<{ onNavigateToRebalancing?: () => void }> = ({
  onNavigateToRebalancing,
}) => {
  const { token, persona } = useAuth();
  const [holdings, setHoldings] = useState<HoldingsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadHoldings = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getHoldings(token);
      setHoldings(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load holdings.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadHoldings();
  }, [token, persona]);

  if (isLoading) {
    return <LoadingSpinner message="Valuating portfolio holdings against latest NAV..." />;
  }

  if (error || !holdings) {
    return (
      <div className="feature-page holdings-page">
        <div className="page-header">
          <h2 className="page-title">Portfolio Holdings & Allocation Drift</h2>
        </div>
        <Alert type="error" title="Holdings Unavailable" message={error || 'No holdings data found.'} />
      </div>
    );
  }

  return (
    <div className="feature-page holdings-page">
      <div className="page-header">
        <div>
          <h2 className="page-title">Portfolio Holdings & Allocation Drift</h2>
          <p className="page-subtitle">
            Real-time portfolio valuation per asset class compared against target allocation thresholds.
          </p>
        </div>
        <div className="page-header__actions">
          {holdings.portfolio_breached && onNavigateToRebalancing && (
            <button
              type="button"
              className="btn btn--danger animate-pulse"
              onClick={onNavigateToRebalancing}
              id="view-rebalance-proposal-btn"
            >
              ⚠️ Rebalance Portfolio
            </button>
          )}
        </div>
      </div>

      {!holdings.has_target && (
        <Alert
          type="info"
          title="No Target Recommendation"
          message="Your holdings are valued below, but target allocations and drift are not calculated because you do not have an active portfolio recommendation yet."
        />
      )}

      {holdings.portfolio_breached && (
        <Alert
          type="warning"
          title="Drift Threshold Breached"
          message={`One or more asset classes have drifted by more than ${holdings.drift_threshold_pct}% from your target allocation. A rebalancing action is recommended.`}
        />
      )}

      <div className="kpi-grid">
        <StatCard
          title="Total Portfolio Valuation"
          value={<FormattedMoney value={holdings.total_value} />}
          subtitle={`As of NAV feed date ${holdings.nav_date}`}
          variant="emerald"
          icon="💼"
        />

        <StatCard
          title="Portfolio Balance Status"
          value={
            holdings.portfolio_breached ? (
              <Badge variant="breached" size="lg">
                DRIFT BREACH
              </Badge>
            ) : (
              <Badge variant="balanced" size="lg">
                BALANCED
              </Badge>
            )
          }
          subtitle={
            holdings.drift_threshold_pct
              ? `Threshold: ${holdings.drift_threshold_pct}% (Template v${holdings.template_version_no})`
              : 'Target not set'
          }
          variant={holdings.portfolio_breached ? 'rose' : 'emerald'}
          icon={holdings.portfolio_breached ? '⚠️' : '✅'}
        />

        <StatCard
          title="Asset Classes Tracked"
          value={holdings.lines.length}
          subtitle="Equity, Debt, Gold, Cash"
          variant="indigo"
          icon="📊"
        />
      </div>

      <div className="card holdings-card">
        <div className="card__header">
          <div>
            <h3 className="card__title">Holdings Valuation & Drift Breakdown</h3>
            <span className="card__subtitle">
              Calculated using strict fixed-point arithmetic (NFR-01) with half-even rounding
            </span>
          </div>
        </div>

        <HoldingsTable holdings={holdings} />
      </div>
    </div>
  );
};
