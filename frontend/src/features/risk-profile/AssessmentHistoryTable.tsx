import React from 'react';
import type { HistoryEntryOut } from '../../types/risk_profile';
import { Badge } from '../../components/common/Badge';

interface AssessmentHistoryTableProps {
  history: HistoryEntryOut[];
}

export const AssessmentHistoryTable: React.FC<AssessmentHistoryTableProps> = ({ history }) => {
  if (history.length === 0) {
    return null;
  }

  const bandVariant = (band: string) => {
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
    <div className="card history-card">
      <div className="card__header">
        <h3 className="card__title">Risk Event History</h3>
        <span className="card__subtitle">Append-only audit trail of assessments & overrides</span>
      </div>

      <div className="table-responsive">
        <table className="data-table" aria-label="Risk Assessment History">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Event Type</th>
              <th>Resulting Band</th>
              <th>Policy / Reason</th>
            </tr>
          </thead>
          <tbody>
            {history.map((entry) => (
              <tr key={entry.id}>
                <td>{new Date(entry.created_at).toLocaleString()}</td>
                <td>
                  <Badge variant={entry.type === 'ADVISOR_OVERRIDE' ? 'warning' : 'info'} size="sm">
                    {entry.type === 'ADVISOR_OVERRIDE' ? 'Advisor Override' : 'Assessment'}
                  </Badge>
                </td>
                <td>
                  <Badge variant={bandVariant(entry.band)} size="sm">
                    {entry.band}
                  </Badge>
                </td>
                <td className="text-muted">
                  {entry.type === 'ADVISOR_OVERRIDE'
                    ? entry.reason_code || 'Override Note'
                    : `Risk Policy v${entry.policy_version_no || 1}`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
