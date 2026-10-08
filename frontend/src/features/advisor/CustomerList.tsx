import React from 'react';
import type { AdvisorCustomerOut } from '../../types/advisor';
import { Badge } from '../../components/common/Badge';

interface CustomerListProps {
  customers: AdvisorCustomerOut[];
  onSelectCustomer: (customer: AdvisorCustomerOut) => void;
  onOpenRiskOverride: (customer: AdvisorCustomerOut) => void;
  onOpenManualRec: (customer: AdvisorCustomerOut) => void;
}

export const CustomerList: React.FC<CustomerListProps> = ({
  customers,
  onSelectCustomer,
  onOpenRiskOverride,
  onOpenManualRec,
}) => {
  const bandVariant = (band: string | null) => {
    switch (band) {
      case 'CONSERVATIVE':
        return 'conservative';
      case 'MODERATE':
        return 'moderate';
      case 'AGGRESSIVE':
        return 'aggressive';
      default:
        return 'neutral';
    }
  };

  return (
    <div className="card customer-list-card">
      <div className="card__header">
        <div>
          <h3 className="card__title">Assigned Client Accounts</h3>
          <span className="card__subtitle">Portfolio health, risk band assignment, and drift status</span>
        </div>
      </div>

      <div className="table-responsive">
        <table className="data-table" aria-label="Advisor Assigned Customers Table">
          <thead>
            <tr>
              <th>Client Name</th>
              <th>Effective Risk Band</th>
              <th>Band Source</th>
              <th>Drift Status</th>
              <th>Rebalance Alert</th>
              <th className="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {customers.map((c) => {
              const isBreached = c.portfolio_breached;
              return (
                <tr key={c.customer_id} id={`advisor-customer-${c.customer_id}`}>
                  <td className="font-semibold">{c.display_name}</td>
                  <td>
                    {c.effective_band ? (
                      <Badge variant={bandVariant(c.effective_band)} size="sm">
                        {c.effective_band}
                      </Badge>
                    ) : (
                      <span className="text-muted">Unassessed</span>
                    )}
                  </td>
                  <td>
                    {c.band_source ? (
                      <Badge
                        variant={c.band_source === 'ADVISOR_OVERRIDE' ? 'warning' : 'neutral'}
                        size="sm"
                      >
                        {c.band_source === 'ADVISOR_OVERRIDE' ? 'Override' : 'Assessment'}
                      </Badge>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td>
                    {isBreached ? (
                      <Badge variant="breached" size="sm">
                        ⚠️ BREACHED
                      </Badge>
                    ) : (
                      <Badge variant="balanced" size="sm">
                        BALANCED
                      </Badge>
                    )}
                  </td>
                  <td>
                    {c.open_rebalance_id ? (
                      <Badge variant="warning" size="sm">
                        Proposal Open
                      </Badge>
                    ) : (
                      <span className="text-muted">None</span>
                    )}
                  </td>
                  <td className="text-right table-actions">
                    <button
                      type="button"
                      className="btn btn--sm btn--primary"
                      onClick={() => onSelectCustomer(c)}
                      id={`view-portfolio-btn-${c.customer_id}`}
                    >
                      Portfolio
                    </button>
                    <button
                      type="button"
                      className="btn btn--sm btn--outline"
                      onClick={() => onOpenRiskOverride(c)}
                      id={`risk-override-btn-${c.customer_id}`}
                    >
                      Override Band
                    </button>
                    <button
                      type="button"
                      className="btn btn--sm btn--outline"
                      onClick={() => onOpenManualRec(c)}
                      id={`manual-rec-btn-${c.customer_id}`}
                    >
                      Manual Rec
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
