import React from 'react';
import type { RecommendationOut } from '../../types/recommendation';
import { AllocationBar } from '../../components/common/AllocationBar';
import { FormattedPercent } from '../../components/common/FormattedPercent';
import { Badge } from '../../components/common/Badge';

interface AllocationBreakdownProps {
  recommendation: RecommendationOut;
  onGenerateNew?: () => void;
  isGenerating?: boolean;
}

const ASSET_DETAILS: Record<
  string,
  { name: string; desc: string; icon: string; color: string }
> = {
  EQUITY: {
    name: 'Equities & Stocks',
    desc: 'Public equities index funds targeting high capital appreciation',
    icon: '📈',
    color: '#818cf8',
  },
  DEBT: {
    name: 'Fixed Income & Debt',
    desc: 'Government & corporate bonds offering capital stability and yield',
    icon: '🏛️',
    color: '#38bdf8',
  },
  GOLD: {
    name: 'Gold & Commodities',
    desc: 'Precious metals hedge against inflation and currency debasement',
    icon: '🪙',
    color: '#fbbf24',
  },
  CASH: {
    name: 'Cash & Equivalents',
    desc: 'Liquid treasury instruments for rebalancing liquidity and safety',
    icon: '💵',
    color: '#34d399',
  },
};

export const AllocationBreakdown: React.FC<AllocationBreakdownProps> = ({
  recommendation,
  onGenerateNew,
  isGenerating = false,
}) => {
  const segments = recommendation.allocation.map((a) => ({
    assetClass: a.asset_class,
    targetPct: a.target_pct,
    color: ASSET_DETAILS[a.asset_class]?.color,
  }));

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
    <div className="recommendation-breakdown">
      <div className="card recommendation-hero-card">
        <div className="rec-hero-header">
          <div>
            <div className="rec-tag-row">
              <span className="rec-source-label">Source: {recommendation.source}</span>
              <Badge variant={bandVariant(recommendation.risk_band)} size="md">
                {recommendation.risk_band} BAND
              </Badge>
              <Badge variant="neutral" size="sm">
                Template v{recommendation.template_version_no}
              </Badge>
            </div>
            <h3 className="rec-hero-title">Target Portfolio Allocation</h3>
          </div>
          {onGenerateNew && (
            <button
              type="button"
              className="btn btn--primary"
              onClick={onGenerateNew}
              disabled={isGenerating}
              id="generate-recommendation-btn"
            >
              {isGenerating ? 'Generating...' : '⚡ Generate New Recommendation'}
            </button>
          )}
        </div>

        {recommendation.horizon_months && (
          <div className="horizon-alert">
            <span className="horizon-icon">⏱️</span>
            <div>
              <strong>Goal Horizon Rule Applied: {recommendation.horizon_rule}</strong>
              <p>
                Adjusted for {recommendation.horizon_months} month horizon on primary goal.
              </p>
            </div>
          </div>
        )}

        <div className="rec-bar-container">
          <AllocationBar segments={segments} showLabels={true} />
        </div>
      </div>

      <div className="rec-cards-grid">
        {recommendation.allocation.map((item) => {
          const detail = ASSET_DETAILS[item.asset_class] || {
            name: item.asset_class,
            desc: 'Asset class investment line',
            icon: '📦',
            color: '#94a3b8',
          };
          return (
            <div
              key={item.asset_class}
              className="card asset-rec-card"
              style={{ borderLeftColor: detail.color, borderLeftWidth: '4px' }}
            >
              <div className="asset-rec-card__top">
                <span className="asset-icon">{detail.icon}</span>
                <span className="asset-pct-badge">
                  <FormattedPercent value={item.target_pct} />
                </span>
              </div>
              <h4 className="asset-name">{detail.name}</h4>
              <p className="asset-desc">{detail.desc}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
};
