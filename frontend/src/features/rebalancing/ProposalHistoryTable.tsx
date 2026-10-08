import React from 'react';
import type { RebalanceSummaryOut } from '../../types/rebalancing';
import { Badge } from '../../components/common/Badge';

interface ProposalHistoryTableProps {
  history: RebalanceSummaryOut[];
  onSelectProposal: (id: string) => void;
  activeProposalId?: string;
}

export const ProposalHistoryTable: React.FC<ProposalHistoryTableProps> = ({
  history,
  onSelectProposal,
  activeProposalId,
}) => {
  if (history.length === 0) {
    return null;
  }

  const statusVariant = (status: string) => {
    switch (status) {
      case 'PROPOSED':
        return 'warning';
      case 'ACCEPTED':
        return 'success';
      case 'DISMISSED':
        return 'danger';
      case 'EXPIRED':
        return 'neutral';
      default:
        return 'neutral';
    }
  };

  return (
    <div className="card history-card">
      <div className="card__header">
        <h3 className="card__title">Rebalancing History</h3>
        <span className="card__subtitle">Historical proposals and decision records</span>
      </div>

      <div className="table-responsive">
        <table className="data-table" aria-label="Rebalancing History Table">
          <thead>
            <tr>
              <th>Proposal Date</th>
              <th>NAV Date</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {history.map((item) => {
              const isSelected = item.id === activeProposalId;
              return (
                <tr key={item.id} className={isSelected ? 'row--selected' : ''}>
                  <td>{new Date(item.created_at).toLocaleString()}</td>
                  <td>{item.nav_date}</td>
                  <td>
                    <Badge variant={statusVariant(item.status)} size="sm">
                      {item.status}
                    </Badge>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn btn--text"
                      onClick={() => onSelectProposal(item.id)}
                    >
                      View Details →
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
