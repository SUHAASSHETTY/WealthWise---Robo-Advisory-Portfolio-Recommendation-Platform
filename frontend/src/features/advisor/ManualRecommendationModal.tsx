import React, { useState } from 'react';
import { Modal } from '../../components/common/Modal';
import type { AdvisorCustomerOut, ManualRecommendationIn } from '../../types/advisor';
import { AllocationBar } from '../../components/common/AllocationBar';

interface ManualRecommendationModalProps {
  customer: AdvisorCustomerOut | null;
  onClose: () => void;
  onSubmit: (customerId: string, data: ManualRecommendationIn) => Promise<void>;
  isSubmitting?: boolean;
}

export const ManualRecommendationModal: React.FC<ManualRecommendationModalProps> = ({
  customer,
  onClose,
  onSubmit,
  isSubmitting = false,
}) => {
  const [equity, setEquity] = useState('40.00');
  const [debt, setDebt] = useState('40.00');
  const [gold, setGold] = useState('10.00');
  const [cash, setCash] = useState('10.00');
  const [note, setNote] = useState('Custom allocation tailored to client tax and liquidity requirements.');
  const [error, setError] = useState<string | null>(null);

  if (!customer) return null;

  const eqNum = parseFloat(equity) || 0;
  const debtNum = parseFloat(debt) || 0;
  const goldNum = parseFloat(gold) || 0;
  const cashNum = parseFloat(cash) || 0;
  const total = (eqNum + debtNum + goldNum + cashNum).toFixed(2);
  const isValidSum = total === '100.00';

  const segments = [
    { assetClass: 'EQUITY', targetPct: equity },
    { assetClass: 'DEBT', targetPct: debt },
    { assetClass: 'GOLD', targetPct: gold },
    { assetClass: 'CASH', targetPct: cash },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!isValidSum) {
      setError(`Allocations must sum to exactly 100.00% (currently ${total}%).`);
      return;
    }

    if (note.trim().length < 5) {
      setError('Please provide an advisory note explaining this custom target allocation.');
      return;
    }

    try {
      await onSubmit(customer.customer_id, {
        allocation: [
          { asset_class: 'EQUITY', target_pct: equity },
          { asset_class: 'DEBT', target_pct: debt },
          { asset_class: 'GOLD', target_pct: gold },
          { asset_class: 'CASH', target_pct: cash },
        ],
        note: note.trim(),
      });
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to submit recommendation.';
      setError(msg);
    }
  };

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title={`Manual Recommendation: ${customer.display_name}`}
      size="lg"
    >
      <form onSubmit={handleSubmit} className="advisor-form">
        <p className="modal-desc">
          Craft a bespoke target asset allocation for this client. All 4 asset classes must be
          specified and sum to exactly 100.00%.
        </p>

        {error && <div className="alert alert--danger">{error}</div>}

        <div className="alloc-preview-box">
          <AllocationBar segments={segments} showLabels={true} />
          <div className="total-sum-row">
            <span>Cumulative Total:</span>
            <span className={`sum-badge ${isValidSum ? 'sum-badge--valid' : 'sum-badge--invalid'}`}>
              {total}% {isValidSum ? '✓ Valid (100.00%)' : '✗ Must equal 100.00%'}
            </span>
          </div>
        </div>

        <div className="alloc-inputs-grid">
          <div className="form-group">
            <label htmlFor="alloc-equity" className="form-label">
              Equity (%)
            </label>
            <input
              id="alloc-equity"
              type="text"
              className="form-input"
              value={equity}
              onChange={(e) => setEquity(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="alloc-debt" className="form-label">
              Debt (%)
            </label>
            <input
              id="alloc-debt"
              type="text"
              className="form-input"
              value={debt}
              onChange={(e) => setDebt(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="alloc-gold" className="form-label">
              Gold (%)
            </label>
            <input
              id="alloc-gold"
              type="text"
              className="form-input"
              value={gold}
              onChange={(e) => setGold(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="alloc-cash" className="form-label">
              Cash (%)
            </label>
            <input
              id="alloc-cash"
              type="text"
              className="form-input"
              value={cash}
              onChange={(e) => setCash(e.target.value)}
              required
            />
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="manual-rec-note" className="form-label">
            Advisory Rationale Note
          </label>
          <textarea
            id="manual-rec-note"
            className="form-textarea"
            rows={3}
            placeholder="Explain why this custom allocation was chosen..."
            value={note}
            onChange={(e) => setNote(e.target.value)}
            required
          />
        </div>

        <div className="form-actions">
          <button type="button" className="btn btn--outline" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </button>
          <button
            type="submit"
            className="btn btn--primary"
            disabled={isSubmitting || !isValidSum}
            id="submit-manual-rec-btn"
          >
            {isSubmitting ? 'Recording Recommendation...' : 'Issue Manual Recommendation'}
          </button>
        </div>
      </form>
    </Modal>
  );
};
