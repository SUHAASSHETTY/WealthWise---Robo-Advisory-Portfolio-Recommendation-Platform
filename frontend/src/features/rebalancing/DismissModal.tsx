import React, { useState } from 'react';
import { Modal } from '../../components/common/Modal';

interface DismissModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (reason: string) => Promise<void>;
  isSubmitting?: boolean;
}

const DISMISS_REASONS = [
  { code: 'MARKET_VOLATILITY', label: 'Market Volatility — Prefer to wait for market stabilization' },
  { code: 'TAX_IMPLICATIONS', label: 'Tax Considerations — Deferring capital gains realization' },
  { code: 'LIQUIDITY_NEEDS', label: 'Client Liquidity Needs — Upcoming cash requirement' },
  { code: 'CLIENT_PREFERENCE', label: 'Client Preference — Discretionary hold' },
  { code: 'OTHER', label: 'Other' },
];

export const DismissModal: React.FC<DismissModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  isSubmitting = false,
}) => {
  const [selectedReason, setSelectedReason] = useState(DISMISS_REASONS[0]?.code || 'MARKET_VOLATILITY');
  const [customNote, setCustomNote] = useState('');

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    const reasonText =
      selectedReason === 'OTHER' && customNote.trim()
        ? `OTHER: ${customNote.trim()}`
        : selectedReason;
    await onConfirm(reasonText);
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Dismiss Rebalancing Proposal">
      <form onSubmit={handleConfirm} className="dismiss-form">
        <p className="modal-desc">
          Please select a reason for dismissing this rebalancing proposal. An append-only audit record
          will be recorded.
        </p>

        <div className="form-group">
          <label htmlFor="dismiss-reason" className="form-label">
            Reason Code
          </label>
          <select
            id="dismiss-reason"
            className="form-select"
            value={selectedReason}
            onChange={(e) => setSelectedReason(e.target.value)}
          >
            {DISMISS_REASONS.map((r) => (
              <option key={r.code} value={r.code}>
                {r.label}
              </option>
            ))}
          </select>
        </div>

        {selectedReason === 'OTHER' && (
          <div className="form-group">
            <label htmlFor="custom-dismiss-note" className="form-label">
              Notes
            </label>
            <textarea
              id="custom-dismiss-note"
              className="form-textarea"
              rows={3}
              placeholder="Provide context for dismissal..."
              value={customNote}
              onChange={(e) => setCustomNote(e.target.value)}
            />
          </div>
        )}

        <div className="form-actions">
          <button type="button" className="btn btn--outline" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </button>
          <button
            type="submit"
            className="btn btn--danger"
            disabled={isSubmitting}
            id="confirm-dismiss-btn"
          >
            {isSubmitting ? 'Dismissing...' : 'Confirm Dismissal'}
          </button>
        </div>
      </form>
    </Modal>
  );
};
