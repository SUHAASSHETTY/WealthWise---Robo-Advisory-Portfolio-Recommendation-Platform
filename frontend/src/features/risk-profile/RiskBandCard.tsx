import React from 'react';
import type { RiskBand, RiskProfileOut } from '../../types/risk_profile';
import { Badge } from '../../components/common/Badge';

interface RiskBandCardProps {
  profile: RiskProfileOut;
  onRetakeQuestionnaire: () => void;
}

const BAND_CONFIG: Record<
  RiskBand,
  {
    title: string;
    description: string;
    icon: string;
    color: string;
    badgeVariant: 'conservative' | 'moderate' | 'aggressive';
    allocationPreview: string;
  }
> = {
  CONSERVATIVE: {
    title: 'Conservative Growth',
    description:
      'Prioritizes capital preservation and stable returns through debt securities and liquid cash.',
    icon: '🛡️',
    color: '#34d399',
    badgeVariant: 'conservative',
    allocationPreview: '20% Equity · 70% Debt · 5% Gold · 5% Cash',
  },
  MODERATE: {
    title: 'Moderate Balanced',
    description:
      'Balanced approach targeting steady capital growth with controlled volatility across asset classes.',
    icon: '⚖️',
    color: '#818cf8',
    badgeVariant: 'moderate',
    allocationPreview: '50% Equity · 35% Debt · 10% Gold · 5% Cash',
  },
  AGGRESSIVE: {
    title: 'Aggressive Capital Appreciation',
    description:
      'Maximizes long-term returns by heavily weighting equities and high-growth opportunities.',
    icon: '🚀',
    color: '#fb7185',
    badgeVariant: 'aggressive',
    allocationPreview: '75% Equity · 15% Debt · 7.5% Gold · 2.5% Cash',
  },
};

export const RiskBandCard: React.FC<RiskBandCardProps> = ({ profile, onRetakeQuestionnaire }) => {
  if (!profile.risk_band) {
    return (
      <div className="card risk-card risk-card--empty">
        <div className="risk-card__empty-icon">📋</div>
        <h3 className="risk-card__empty-title">No Risk Profile Assessed</h3>
        <p className="risk-card__empty-desc">
          You haven't completed your risk questionnaire yet. Take the 7-question assessment to unlock
          customized robo-advisory recommendations.
        </p>
        <button
          type="button"
          className="btn btn--primary"
          onClick={onRetakeQuestionnaire}
          id="start-assessment-btn"
        >
          Start Risk Assessment
        </button>
      </div>
    );
  }

  const bandConfig = BAND_CONFIG[profile.risk_band] || {
    title: profile.risk_band,
    description: 'Assigned risk tolerance category.',
    icon: '📌',
    color: '#818cf8',
    badgeVariant: 'moderate' as const,
    allocationPreview: 'Custom Allocation',
  };

  const isOverride = profile.source === 'ADVISOR_OVERRIDE';

  return (
    <div className={`card risk-card risk-card--${bandConfig.badgeVariant}`}>
      <div className="risk-card__header">
        <div className="risk-card__icon-badge">{bandConfig.icon}</div>
        <div className="risk-card__title-group">
          <div className="risk-card__tag-row">
            <span className="risk-card__subtitle">Effective Risk Category</span>
            <Badge variant={bandConfig.badgeVariant} size="lg">
              {profile.risk_band}
            </Badge>
            {isOverride && (
              <Badge variant="warning" size="sm">
                ADVISOR OVERRIDE
              </Badge>
            )}
          </div>
          <h2 className="risk-card__title">{bandConfig.title}</h2>
        </div>
      </div>

      <p className="risk-card__description">{bandConfig.description}</p>

      <div className="risk-card__meta">
        <div className="risk-card__meta-item">
          <span className="meta-label">Source</span>
          <span className="meta-value">{isOverride ? 'Advisor Workbench' : 'Questionnaire Scoring'}</span>
        </div>
        {profile.as_of && (
          <div className="risk-card__meta-item">
            <span className="meta-label">Assessed Date</span>
            <span className="meta-value">{new Date(profile.as_of).toLocaleDateString()}</span>
          </div>
        )}
        <div className="risk-card__meta-item">
          <span className="meta-label">Base Allocation</span>
          <span className="meta-value">{bandConfig.allocationPreview}</span>
        </div>
      </div>

      <div className="risk-card__actions">
        <button
          type="button"
          className="btn btn--outline"
          onClick={onRetakeQuestionnaire}
          id="retake-assessment-btn"
        >
          Retake Assessment
        </button>
      </div>
    </div>
  );
};
