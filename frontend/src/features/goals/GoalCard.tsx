import React from 'react';
import type { GoalOut } from '../../types/goals';
import { FormattedMoney } from '../../components/common/FormattedMoney';
import { FormattedPercent } from '../../components/common/FormattedPercent';
import { Badge } from '../../components/common/Badge';

interface GoalCardProps {
  goal: GoalOut;
  onViewDetails?: (goal: GoalOut) => void;
}

const GOAL_ICONS: Record<string, string> = {
  EDUCATION: '🎓',
  RETIREMENT: '🌴',
  HOME: '🏡',
  EMERGENCY: '🛡️',
  WEALTH: '💎',
  OTHER: '🎯',
};

export const GoalCard: React.FC<GoalCardProps> = ({ goal, onViewDetails }) => {
  const icon = GOAL_ICONS[goal.goal_type.toUpperCase()] || '🎯';
  const progress = goal.progress;
  const percentComplete = progress ? parseFloat(progress.percent_complete || '0') : 0;
  const isAchieved = progress?.status === 'ACHIEVED' || percentComplete >= 100;

  return (
    <div className={`card goal-card ${isAchieved ? 'goal-card--achieved' : ''}`} id={`goal-${goal.id}`}>
      <div className="goal-card__header">
        <div className="goal-card__icon-box">{icon}</div>
        <div className="goal-card__title-box">
          <div className="goal-card__tag-row">
            <span className="goal-card__priority-badge">Priority {goal.priority}</span>
            <span className="goal-card__type-tag">{goal.goal_type}</span>
            {isAchieved ? (
              <Badge variant="achieved" size="sm">
                ACHIEVED
              </Badge>
            ) : (
              <Badge variant="in_progress" size="sm">
                IN PROGRESS
              </Badge>
            )}
          </div>
          <h3 className="goal-card__name">{goal.name}</h3>
        </div>
      </div>

      <div className="goal-card__metrics">
        <div className="goal-metric">
          <span className="metric-label">Target Amount</span>
          <span className="metric-value">
            <FormattedMoney value={goal.target_amount} />
          </span>
        </div>
        <div className="goal-metric">
          <span className="metric-label">Current Value</span>
          <span className="metric-value">
            <FormattedMoney value={progress?.current_goal_value || '0.00'} />
          </span>
        </div>
        <div className="goal-metric">
          <span className="metric-label">Target Date</span>
          <span className="metric-value">{goal.target_date}</span>
        </div>
        <div className="goal-metric">
          <span className="metric-label">Funding Share</span>
          <span className="metric-value">
            <FormattedPercent value={goal.funding_share_pct} />
          </span>
        </div>
      </div>

      <div className="goal-card__progress-section">
        <div className="goal-progress-header">
          <span className="progress-label">Goal Completion</span>
          <span className="progress-percent">
            <FormattedPercent value={progress?.percent_complete || '0.00'} />
          </span>
        </div>
        <div
          className="progress-track"
          role="progressbar"
          aria-valuenow={Math.min(percentComplete, 100)}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className={`progress-fill ${isAchieved ? 'progress-fill--achieved' : ''}`}
            style={{ width: `${Math.min(Math.max(percentComplete, 0), 100)}%` }}
          />
        </div>
      </div>

      {progress?.nav_date && (
        <div className="goal-card__footer">
          <span className="nav-date-note">As of NAV {progress.nav_date}</span>
          {onViewDetails && (
            <button
              type="button"
              className="btn btn--text"
              onClick={() => onViewDetails(goal)}
            >
              History →
            </button>
          )}
        </div>
      )}
    </div>
  );
};
