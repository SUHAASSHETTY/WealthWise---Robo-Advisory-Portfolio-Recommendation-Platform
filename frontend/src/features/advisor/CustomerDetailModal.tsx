import React, { useEffect, useState } from 'react';
import { Modal } from '../../components/common/Modal';
import { getAdvisorCustomerPortfolio, getCustomerAuditTrail } from '../../api/advisorApi';
import type {
  AdvisorCustomerPortfolioOut,
  AuditEventOut,
} from '../../types/advisor';
import { HoldingsTable } from '../holdings/HoldingsTable';
import { FormattedMoney } from '../../components/common/FormattedMoney';
import { FormattedPercent } from '../../components/common/FormattedPercent';
import { Badge } from '../../components/common/Badge';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';

interface CustomerDetailModalProps {
  customerId: string | null;
  token: string;
  onClose: () => void;
}

export const CustomerDetailModal: React.FC<CustomerDetailModalProps> = ({
  customerId,
  token,
  onClose,
}) => {
  const [portfolio, setPortfolio] = useState<AdvisorCustomerPortfolioOut | null>(null);
  const [auditTrail, setAuditTrail] = useState<AuditEventOut[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'holdings' | 'goals' | 'recommendation' | 'audit'>('holdings');

  useEffect(() => {
    if (!customerId) return;
    setIsLoading(true);
    Promise.all([
      getAdvisorCustomerPortfolio(token, customerId),
      getCustomerAuditTrail(token, customerId),
    ])
      .then(([p, a]) => {
        setPortfolio(p);
        setAuditTrail(a);
      })
      .finally(() => setIsLoading(false));
  }, [customerId, token]);

  if (!customerId) return null;

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title={`Client Portfolio Overview: ${portfolio?.customer.display_name || 'Loading...'}`}
      size="xl"
    >
      {isLoading || !portfolio ? (
        <LoadingSpinner message="Loading client overview and portfolio drilldown..." />
      ) : (
        <div className="advisor-portfolio-modal">
          <div className="client-meta-strip">
            <div className="meta-block">
              <span className="meta-label">Client ID</span>
              <span className="meta-val font-mono">{portfolio.customer.id.substring(0, 8)}...</span>
            </div>
            <div className="meta-block">
              <span className="meta-label">KYC Status</span>
              <span className="meta-val">
                {portfolio.customer.kyc_verified ? (
                  <Badge variant="success" size="sm">
                    Verified
                  </Badge>
                ) : (
                  <Badge variant="danger" size="sm">
                    Unverified
                  </Badge>
                )}
              </span>
            </div>
            <div className="meta-block">
              <span className="meta-label">Effective Risk Band</span>
              <span className="meta-val">
                <Badge variant="neutral" size="sm">
                  {portfolio.risk_profile.band || 'Unassessed'}
                </Badge>
              </span>
            </div>
            <div className="meta-block">
              <span className="meta-label">Total Valuation</span>
              <span className="meta-val font-semibold">
                <FormattedMoney value={portfolio.holdings.total_value} />
              </span>
            </div>
            <div className="meta-block">
              <span className="meta-label">Drift Status</span>
              <span className="meta-val">
                {portfolio.holdings.portfolio_breached ? (
                  <Badge variant="breached" size="sm">
                    ⚠️ BREACHED
                  </Badge>
                ) : (
                  <Badge variant="balanced" size="sm">
                    BALANCED
                  </Badge>
                )}
              </span>
            </div>
          </div>

          <div className="tab-nav">
            <button
              type="button"
              className={`tab-btn ${activeTab === 'holdings' ? 'tab-btn--active' : ''}`}
              onClick={() => setActiveTab('holdings')}
            >
              💼 Holdings & Drift
            </button>
            <button
              type="button"
              className={`tab-btn ${activeTab === 'goals' ? 'tab-btn--active' : ''}`}
              onClick={() => setActiveTab('goals')}
            >
              🎯 Goals ({portfolio.goals.length})
            </button>
            <button
              type="button"
              className={`tab-btn ${activeTab === 'recommendation' ? 'tab-btn--active' : ''}`}
              onClick={() => setActiveTab('recommendation')}
            >
              📊 Target Recommendation
            </button>
            <button
              type="button"
              className={`tab-btn ${activeTab === 'audit' ? 'tab-btn--active' : ''}`}
              onClick={() => setActiveTab('audit')}
            >
              📜 Audit Trail ({auditTrail.length})
            </button>
          </div>

          <div className="tab-content">
            {activeTab === 'holdings' && (
              <div className="tab-pane">
                <HoldingsTable holdings={portfolio.holdings} />
              </div>
            )}

            {activeTab === 'goals' && (
              <div className="tab-pane">
                {portfolio.goals.length === 0 ? (
                  <p className="empty-text">No investment goals found for this client.</p>
                ) : (
                  <div className="table-responsive">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Goal Name</th>
                          <th>Category</th>
                          <th>Priority</th>
                          <th className="text-right">Target Amount</th>
                          <th className="text-right">Funding Share</th>
                          <th className="text-right">Current Value</th>
                          <th className="text-right">Progress</th>
                        </tr>
                      </thead>
                      <tbody>
                        {portfolio.goals.map((g) => (
                          <tr key={g.id}>
                            <td className="font-semibold">{g.name}</td>
                            <td>{g.goal_type}</td>
                            <td>Priority {g.priority}</td>
                            <td className="text-right">
                              <FormattedMoney value={g.target_amount} />
                            </td>
                            <td className="text-right">
                              <FormattedPercent value={g.funding_share_pct} />
                            </td>
                            <td className="text-right">
                              <FormattedMoney value={g.progress?.current_goal_value || '0.00'} />
                            </td>
                            <td className="text-right font-semibold">
                              <FormattedPercent value={g.progress?.percent_complete || '0.00'} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'recommendation' && (
              <div className="tab-pane">
                {portfolio.latest_recommendation ? (
                  <div className="rec-summary-box">
                    <div className="rec-summary-header">
                      <h4>
                        Active Target Recommendation (Template v{portfolio.latest_recommendation.template_version_no})
                      </h4>
                      <Badge variant="neutral" size="sm">
                        {portfolio.latest_recommendation.source}
                      </Badge>
                    </div>
                    <div className="alloc-list">
                      {portfolio.latest_recommendation.allocation.map((a) => (
                        <div key={a.asset_class} className="alloc-row">
                          <span className="alloc-asset">{a.asset_class}</span>
                          <span className="alloc-val">
                            <FormattedPercent value={a.target_pct} />
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <p className="empty-text">No target recommendation has been generated yet.</p>
                )}
              </div>
            )}

            {activeTab === 'audit' && (
              <div className="tab-pane">
                {auditTrail.length === 0 ? (
                  <p className="empty-text">No audit events recorded for this customer.</p>
                ) : (
                  <div className="table-responsive">
                    <table className="data-table audit-table">
                      <thead>
                        <tr>
                          <th>Timestamp</th>
                          <th>Action</th>
                          <th>Actor</th>
                          <th>Entity</th>
                        </tr>
                      </thead>
                      <tbody>
                        {auditTrail.map((ev, idx) => (
                          <tr key={idx}>
                            <td>{new Date(ev.occurred_at).toLocaleString()}</td>
                            <td className="font-semibold">{ev.action}</td>
                            <td>
                              <Badge variant="neutral" size="sm">
                                {ev.actor_role}
                              </Badge>
                            </td>
                            <td>
                              {ev.entity_type} ({ev.entity_id.substring(0, 8)}...)
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </Modal>
  );
};
