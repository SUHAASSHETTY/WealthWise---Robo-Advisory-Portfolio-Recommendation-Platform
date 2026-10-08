import React, { useState } from 'react';
import { Modal } from '../../components/common/Modal';
import type { AdvisorCustomerOut, RiskOverrideIn } from '../../types/advisor';

interface RiskOverrideModalProps {
  customer: AdvisorCustomerOut | null;
  onClose: () => void;
  onSubmit: (customerId: string, data: RiskOverrideIn) => Promise<void>;
  isSubmitting?: boolean;
}

const REASON_CODES = [
  { code: 'CLIENT_CIRCUMSTANCES_CHANGED', label: 'Client Circumstances Changed (e.g. retirement approaching)' },
  { code: 'MARKET_CONDITIONS', label: 'Market Conditions (macro risk adjustments)' },
  { code: 'TAX_OPTIMISATION', label: 'Tax Optimisation (sheltering or timing gains)' },
  { code: 'ADVISOR_DISCRETION', label: 'Advisor Discretion (fiduciary recommendation)' },
];

const BANDS = ['CONSERVATIVE', 'MODERATE', 'AGGRESSIVE'];

export const RiskOverrideModal: React.FC<RiskOverrideModalProps> = ({
  customer,
  onClose,
  onSubmit,
  isSubmitting = false,
}) => {
  const [newBand, setNewBand] = useState('CONSERVATIVE');
  const [reasonCode, setReasonCode] = useState(REASON_CODES[0]?.code || 'CLIENT_CIRCUMSTANCES_CHANGED');
  const [note, setNote] = useState('Client retiring in 18 months; needs capital stability.');
  const [error, setError] = useState<string | null>(null);

  if (!customer) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (newBand === customer.effective_band) {
      setError(`Selected band must be different from the client's current band (${customer.effective_band}).`);
      return;
    }

    if (note.trim().length < 5) {
      setError('Please provide a substantive rationale note (at least 5 characters).');
      return;
    }

    try {
      await onSubmit(customer.customer_id, {
        new_band: newBand,
        reason_code: reasonCode,
        note: note.trim(),
      });
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to submit override.';
      setError(msg);
    }
  };

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title={`Override Risk Band: ${customer.display_name}`}
    >
      <form onSubmit={handleSubmit} className="advisor-form">
        <p className="modal-desc">
          Advisors may override a client's risk band. An immutable audit event and override row will
          be created. The note is preserved in the audit trail.
        </p>

        {error && <div className="alert alert--danger">{error}</div>}

        <div className="current-band-box">
          <span className="box-label">Current Band:</span>
          <span className="box-value">{customer.effective_band || 'Unassessed'}</span>
        </div>

        <div className="form-group">
          <label htmlFor="new-risk-band" className="form-label">
            New Risk Band
          </label>
          <select
            id="new-risk-band"
            className="form-select"
            value={newBand}
            onChange={(e) => setNewBand(e.target.value)}
          >
            {BANDS.map((b) => (
              <option key={b} value={b} disabled={b === customer.effective_band}>
                {b} {b === customer.effective_band ? '(Current)' : ''}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="override-reason-code" className="form-label">
            Reason Code
          </label>
          <select
            id="override-reason-code"
            className="form-select"
            value={reasonCode}
            onChange={(e) => setReasonCode(e.target.value)}
          >
            {REASON_CODES.map((r) => (
              <option key={r.code} value={r.code}>
                {r.label}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="override-note" className="form-label">
            Advisor Rationale Note
          </label>
          <textarea
            id="override-note"
            className="form-textarea"
            rows={3}
            placeholder="Explain the fiduciary rationale for this risk band change..."
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
            disabled={isSubmitting}
            id="submit-risk-override-btn"
          >
            {isSubmitting ? 'Recording Override...' : 'Apply Risk Override'}
          </button>
        </div>
      </form>
    </Modal>
  );
};
