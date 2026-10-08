import React, { useState } from 'react';
import { Modal } from '../../components/common/Modal';
import type { GoalCreateIn } from '../../types/goals';

interface GoalCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: GoalCreateIn) => Promise<void>;
  nextPriority: number;
}

const GOAL_TYPES = ['EDUCATION', 'RETIREMENT', 'HOME', 'EMERGENCY', 'WEALTH', 'OTHER'];

export const GoalCreateModal: React.FC<GoalCreateModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  nextPriority,
}) => {
  const [name, setName] = useState('');
  const [goalType, setGoalType] = useState('EDUCATION');
  const [targetAmount, setTargetAmount] = useState('50000.00');
  const [targetDate, setTargetDate] = useState('2032-12-31');
  const [priority, setPriority] = useState(String(nextPriority));
  const [fundingSharePct, setFundingSharePct] = useState('40.00');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!name.trim()) {
      setError('Please provide a goal name.');
      return;
    }

    const amt = parseFloat(targetAmount);
    if (isNaN(amt) || amt <= 0) {
      setError('Target amount must be a positive number.');
      return;
    }

    const share = parseFloat(fundingSharePct);
    if (isNaN(share) || share <= 0 || share > 100) {
      setError('Funding share must be between 0.01% and 100.00%.');
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit({
        name: name.trim(),
        goal_type: goalType,
        target_amount: targetAmount,
        target_date: targetDate,
        priority: parseInt(priority, 10) || 1,
        funding_share_pct: fundingSharePct,
      });
      // Reset form
      setName('');
      setTargetAmount('50000.00');
      setFundingSharePct('40.00');
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create goal.';
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create New Investment Goal">
      <form className="goal-create-form" onSubmit={handleSubmit}>
        {error && <div className="alert alert--danger">{error}</div>}

        <div className="form-group">
          <label htmlFor="goal-name" className="form-label">
            Goal Name
          </label>
          <input
            id="goal-name"
            type="text"
            className="form-input"
            placeholder="e.g. Daughter's university corpus"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>

        <div className="form-grid">
          <div className="form-group">
            <label htmlFor="goal-type" className="form-label">
              Category
            </label>
            <select
              id="goal-type"
              className="form-select"
              value={goalType}
              onChange={(e) => setGoalType(e.target.value)}
            >
              {GOAL_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="goal-priority" className="form-label">
              Priority Order
            </label>
            <input
              id="goal-priority"
              type="number"
              min="1"
              max="20"
              className="form-input"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              required
            />
          </div>
        </div>

        <div className="form-grid">
          <div className="form-group">
            <label htmlFor="goal-target-amount" className="form-label">
              Target Amount ($)
            </label>
            <input
              id="goal-target-amount"
              type="text"
              className="form-input"
              placeholder="50000.00"
              value={targetAmount}
              onChange={(e) => setTargetAmount(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="goal-funding-share" className="form-label">
              Funding Share (%)
            </label>
            <input
              id="goal-funding-share"
              type="text"
              className="form-input"
              placeholder="40.00"
              value={fundingSharePct}
              onChange={(e) => setFundingSharePct(e.target.value)}
              required
            />
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="goal-target-date" className="form-label">
            Target Date
          </label>
          <input
            id="goal-target-date"
            type="date"
            className="form-input"
            value={targetDate}
            onChange={(e) => setTargetDate(e.target.value)}
            required
          />
        </div>

        <div className="form-actions">
          <button type="button" className="btn btn--outline" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </button>
          <button type="submit" className="btn btn--primary" disabled={isSubmitting} id="save-goal-btn">
            {isSubmitting ? 'Creating Goal...' : 'Create Goal'}
          </button>
        </div>
      </form>
    </Modal>
  );
};
