import React from 'react';
import type { RebalanceProposalOut } from '../../types/rebalancing';
import { FormattedMoney } from '../../components/common/FormattedMoney';
import { FormattedPercent } from '../../components/common/FormattedPercent';
import { Badge } from '../../components/common/Badge';

interface ProposalCardProps {
  proposal: RebalanceProposalOut;
  onAccept: (id: string) => Promise<void>;
  onOpenDismiss: (id: string) => void;
  isActionLoading?: boolean;
}

const ACTION_COLORS: Record<string, 'buy' | 'sell' | 'hold' | 'neutral'> = {
  BUY: 'buy',
  SELL: 'sell',
  HOLD: 'hold',
};

export const ProposalCard: React.FC<ProposalCardProps> = ({
  proposal,
  onAccept,
  onOpenDismiss,
  isActionLoading = false,
}) => {
  if (!proposal || !proposal.status) {
    return null;
  }

  const status = proposal.status;
  const isProposed = status === 'PROPOSED';
  const isAccepted = status === 'ACCEPTED';
  const isDismissed = status === 'DISMISSED';

  return (
    <div className={`card proposal-card proposal-card--${status.toLowerCase()}`}>
      <div className="proposal-card__header">
        <div>
          <div className="proposal-tag-row">
            <Badge
              variant={
                isProposed
                  ? 'warning'
                  : isAccepted
                    ? 'success'
                    : isDismissed
                      ? 'danger'
                      : 'neutral'
              }
              size="md"
            >
              {proposal.status}
            </Badge>
            <span className="proposal-date">NAV Date: {proposal.nav_date}</span>
            <span className="proposal-threshold">
              Threshold: {proposal.drift_threshold_pct}%
            </span>
          </div>
          <h3 className="proposal-card__title">Rebalancing Trade Recommendation</h3>
        </div>

        {isProposed && (
          <div className="proposal-card__actions">
            <button
              type="button"
              className="btn btn--outline-danger"
              onClick={() => onOpenDismiss(proposal.id)}
              disabled={isActionLoading}
              id="dismiss-proposal-btn"
            >
              Dismiss
            </button>
            <button
              type="button"
              className="btn btn--success"
              onClick={() => onAccept(proposal.id)}
              disabled={isActionLoading}
              id="accept-proposal-btn"
            >
              {isActionLoading ? 'Executing...' : '✓ Accept & Place Orders'}
            </button>
          </div>
        )}
      </div>

      <div className="table-responsive">
        <table className="data-table proposal-table" aria-label="Rebalancing Trade Lines">
          <thead>
            <tr>
              <th>Asset Class</th>
              <th>Action</th>
              <th className="text-right">Current Value</th>
              <th className="text-right">Target %</th>
              <th className="text-right">Units to Trade</th>
              <th className="text-right">Trade Value</th>
            </tr>
          </thead>
          <tbody>
            {proposal.lines.map((line) => {
              const actionVariant = ACTION_COLORS[line.action] || 'neutral';
              const isCash = line.asset_class === 'CASH';
              return (
                <tr key={line.asset_class} className={`trade-row trade-row--${line.action.toLowerCase()}`}>
                  <td className="font-semibold">{line.asset_class}</td>
                  <td>
                    <Badge variant={actionVariant} size="sm">
                      {line.action}
                    </Badge>
                  </td>
                  <td className="text-right">
                    <FormattedMoney value={line.current_value} />
                  </td>
                  <td className="text-right">
                    <FormattedPercent value={line.target_pct} />
                  </td>
                  <td className="text-right font-mono">
                    {isCash ? '—' : line.quantity ? `${line.quantity} units` : '0.0000'}
                  </td>
                  <td className="text-right font-semibold">
                    <FormattedMoney value={line.trade_value} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="proposal-card__footer">
        <div className="cash-settlement-info">
          <span className="info-label">Post-Trade Cash Position</span>
          <span className="info-value font-mono">
            <FormattedMoney value={proposal.post_trade_cash} />
          </span>
        </div>
        {proposal.decision && (
          <div className="decision-info">
            <span className="decision-label">
              Decision: {proposal.decision.decision} by {proposal.decision.actor_role} at{' '}
              {new Date(proposal.decision.created_at).toLocaleString()}
            </span>
            {proposal.decision.reason && (
              <span className="decision-reason">Reason: {proposal.decision.reason}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
