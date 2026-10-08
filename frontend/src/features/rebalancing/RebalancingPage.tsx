import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import {
  acceptRebalancingProposal,
  dismissRebalancingProposal,
  evaluateRebalancing,
  getRebalanceRecommendation,
  listRebalanceRecommendations,
} from '../../api/rebalancingApi';
import type { RebalanceProposalOut, RebalanceSummaryOut } from '../../types/rebalancing';
import { ProposalCard } from './ProposalCard';
import { ProposalHistoryTable } from './ProposalHistoryTable';
import { DismissModal } from './DismissModal';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { Alert } from '../../components/common/Alert';

export const RebalancingPage: React.FC = () => {
  const { token, persona } = useAuth();
  const [activeProposal, setActiveProposal] = useState<RebalanceProposalOut | null>(null);
  const [history, setHistory] = useState<RebalanceSummaryOut[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [dismissModalId, setDismissModalId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadRebalancingData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const summaries = await listRebalanceRecommendations(token);
      setHistory(summaries);

      if (summaries.length > 0) {
        // Find latest or proposed
        const proposed = summaries.find((s) => s.status === 'PROPOSED');
        const targetId = proposed ? proposed.id : summaries[0]?.id;
        if (targetId) {
          const details = await getRebalanceRecommendation(token, targetId);
          setActiveProposal(details);
        } else {
          setActiveProposal(null);
        }
      } else {
        setActiveProposal(null);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load rebalancing proposals.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadRebalancingData();
  }, [token, persona]);

  const handleEvaluate = async () => {
    setIsEvaluating(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await evaluateRebalancing(token);
      if (res && 'status' in res && res.status) {
        setActiveProposal(res as RebalanceProposalOut);
        setSuccessMsg('Rebalancing proposal generated successfully based on current drift breach!');
      } else {
        const reason =
          (res as { reason?: string })?.reason ||
          'Portfolio is within drift threshold limits. No rebalancing required.';
        setSuccessMsg(reason);
      }
      const summaries = await listRebalanceRecommendations(token);
      setHistory(summaries);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to evaluate rebalancing.';
      setError(msg);
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleAccept = async (id: string) => {
    setIsActionLoading(true);
    setError(null);
    try {
      const res = await acceptRebalancingProposal(token, id);
      setSuccessMsg(`Rebalancing proposal accepted! ${res.orders.length} orders placed (FILLED_STUB).`);
      await loadRebalancingData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to accept proposal.';
      setError(msg);
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleDismiss = async (reason: string) => {
    if (!dismissModalId) return;
    setIsActionLoading(true);
    setError(null);
    try {
      await dismissRebalancingProposal(token, dismissModalId, reason);
      setSuccessMsg('Rebalancing proposal dismissed with audit record.');
      await loadRebalancingData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to dismiss proposal.';
      setError(msg);
    } finally {
      setIsActionLoading(false);
      setDismissModalId(null);
    }
  };

  const handleSelectHistoryItem = async (id: string) => {
    try {
      const details = await getRebalanceRecommendation(token, id);
      setActiveProposal(details);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch proposal details.';
      setError(msg);
    }
  };

  if (isLoading) {
    return <LoadingSpinner message="Checking portfolio drift & rebalancing proposals..." />;
  }

  return (
    <div className="feature-page rebalancing-page">
      <div className="page-header">
        <div>
          <h2 className="page-title">Portfolio Drift Rebalancing</h2>
          <p className="page-subtitle">
            Generate and execute rule-based rebalancing trades when asset class drift exceeds threshold limits.
          </p>
        </div>
        <div className="page-header__actions">
          <button
            type="button"
            className="btn btn--primary"
            onClick={handleEvaluate}
            disabled={isEvaluating}
            id="evaluate-rebalance-btn"
          >
            {isEvaluating ? 'Evaluating Drift...' : '⚡ Evaluate Rebalancing'}
          </button>
        </div>
      </div>

      {error && <Alert type="error" title="Error" message={error} onClose={() => setError(null)} />}
      {successMsg && (
        <Alert type="success" title="Success" message={successMsg} onClose={() => setSuccessMsg(null)} />
      )}

      {activeProposal ? (
        <div className="rebalance-content">
          <ProposalCard
            proposal={activeProposal}
            onAccept={handleAccept}
            onOpenDismiss={(id) => setDismissModalId(id)}
            isActionLoading={isActionLoading}
          />
          <ProposalHistoryTable
            history={history}
            onSelectProposal={handleSelectHistoryItem}
            activeProposalId={activeProposal.id}
          />
        </div>
      ) : (
        <div className="card empty-state">
          <div className="empty-state__icon">⚖️</div>
          <h3>No Active Rebalancing Proposals</h3>
          <p>
            Your portfolio either does not have active drift breaches or hasn't had rebalancing
            evaluated recently.
          </p>
          <button
            type="button"
            className="btn btn--primary"
            onClick={handleEvaluate}
            disabled={isEvaluating}
          >
            Evaluate Portfolio Drift Now
          </button>
        </div>
      )}

      <DismissModal
        isOpen={!!dismissModalId}
        onClose={() => setDismissModalId(null)}
        onConfirm={handleDismiss}
        isSubmitting={isActionLoading}
      />
    </div>
  );
};
