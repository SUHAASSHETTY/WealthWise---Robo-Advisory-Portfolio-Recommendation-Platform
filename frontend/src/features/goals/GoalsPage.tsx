import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { createGoal, getGoalProgressHistory, listGoals } from '../../api/goalsApi';
import type { GoalCreateIn, GoalOut, GoalProgressHistoryOut } from '../../types/goals';
import { GoalCard } from './GoalCard';
import { GoalCreateModal } from './GoalCreateModal';
import { LoadingSpinner } from '../../components/common/LoadingSpinner';
import { Alert } from '../../components/common/Alert';
import { Modal } from '../../components/common/Modal';
import { FormattedMoney } from '../../components/common/FormattedMoney';
import { FormattedPercent } from '../../components/common/FormattedPercent';
import { Badge } from '../../components/common/Badge';

export const GoalsPage: React.FC = () => {
  const { token, persona } = useAuth();
  const [goals, setGoals] = useState<GoalOut[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedGoalHistory, setSelectedGoalHistory] = useState<{
    goal: GoalOut;
    history: GoalProgressHistoryOut | null;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadGoals = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await listGoals(token);
      setGoals(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load goals.';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadGoals();
  }, [token, persona]);

  const handleCreateGoal = async (data: GoalCreateIn) => {
    await createGoal(token, data);
    setSuccessMsg(`Goal "${data.name}" created successfully!`);
    await loadGoals();
  };

  const handleViewGoalHistory = async (goal: GoalOut) => {
    try {
      const hist = await getGoalProgressHistory(token, goal.id);
      setSelectedGoalHistory({ goal, history: hist });
    } catch {
      setSelectedGoalHistory({ goal, history: null });
    }
  };

  if (isLoading) {
    return <LoadingSpinner message="Loading your financial goals..." />;
  }

  const nextPriority = goals.length > 0 ? Math.max(...goals.map((g) => g.priority)) + 1 : 1;

  return (
    <div className="feature-page goals-page">
      <div className="page-header">
        <div>
          <h2 className="page-title">Investment Goals Tracker</h2>
          <p className="page-subtitle">
            Track multi-goal portfolios with dedicated funding shares and automatic NAV valuation progress.
          </p>
        </div>
        <button
          type="button"
          className="btn btn--primary"
          onClick={() => setIsCreateModalOpen(true)}
          id="create-goal-btn"
        >
          + Add New Goal
        </button>
      </div>

      {error && <Alert type="error" title="Error" message={error} onClose={() => setError(null)} />}
      {successMsg && (
        <Alert type="success" title="Success" message={successMsg} onClose={() => setSuccessMsg(null)} />
      )}

      {goals.length === 0 ? (
        <div className="card empty-state">
          <div className="empty-state__icon">🎯</div>
          <h3>No Goals Configured</h3>
          <p>You haven't set up any investment goals yet. Create your first goal to track progress over time.</p>
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => setIsCreateModalOpen(true)}
          >
            Create Your First Goal
          </button>
        </div>
      ) : (
        <div className="goals-grid">
          {goals.map((goal) => (
            <GoalCard key={goal.id} goal={goal} onViewDetails={handleViewGoalHistory} />
          ))}
        </div>
      )}

      <GoalCreateModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreateGoal}
        nextPriority={nextPriority}
      />

      {selectedGoalHistory && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedGoalHistory(null)}
          title={`Progress History: ${selectedGoalHistory.goal.name}`}
        >
          <div className="goal-history-modal">
            <div className="modal-summary-box">
              <div>
                <span className="summary-label">Target Amount</span>
                <span className="summary-value">
                  <FormattedMoney value={selectedGoalHistory.goal.target_amount} />
                </span>
              </div>
              <div>
                <span className="summary-label">Funding Share</span>
                <span className="summary-value">
                  <FormattedPercent value={selectedGoalHistory.goal.funding_share_pct} />
                </span>
              </div>
              <div>
                <span className="summary-label">Priority</span>
                <span className="summary-value">{selectedGoalHistory.goal.priority}</span>
              </div>
            </div>

            <div className="table-responsive">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>NAV Date</th>
                    <th>Current Value</th>
                    <th>Completion %</th>
                    <th>Status</th>
                    <th>Trigger</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedGoalHistory.history?.history.map((snap, idx) => (
                    <tr key={idx}>
                      <td>{snap.nav_date}</td>
                      <td>
                        <FormattedMoney value={snap.current_goal_value} />
                      </td>
                      <td>
                        <FormattedPercent value={snap.percent_complete} />
                      </td>
                      <td>
                        <Badge
                          variant={snap.status === 'ACHIEVED' ? 'achieved' : 'in_progress'}
                          size="sm"
                        >
                          {snap.status}
                        </Badge>
                      </td>
                      <td className="text-muted">{snap.reason || 'NAV_REFRESH'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
