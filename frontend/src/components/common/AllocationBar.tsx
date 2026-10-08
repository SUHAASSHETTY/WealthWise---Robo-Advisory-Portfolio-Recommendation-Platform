import React from 'react';

export interface AllocationSegment {
  assetClass: string;
  targetPct: string | number;
  currentPct?: string | number | null;
  label?: string;
  color?: string;
}

const ASSET_COLORS: Record<string, string> = {
  EQUITY: '#818cf8', // Indigo
  DEBT: '#38bdf8', // Sky Blue
  GOLD: '#fbbf24', // Amber Gold
  CASH: '#34d399', // Emerald
};

interface AllocationBarProps {
  segments: AllocationSegment[];
  showLabels?: boolean;
  className?: string;
}

export const AllocationBar: React.FC<AllocationBarProps> = ({
  segments,
  showLabels = true,
  className = '',
}) => {
  return (
    <div className={`allocation-bar-wrapper ${className}`}>
      <div className="allocation-bar" role="progressbar" aria-label="Asset Allocation Distribution">
        {segments.map((segment) => {
          const pct = typeof segment.targetPct === 'number' ? segment.targetPct : parseFloat(segment.targetPct || '0');
          if (pct <= 0) return null;
          const bg = segment.color || ASSET_COLORS[segment.assetClass] || '#94a3b8';
          return (
            <div
              key={segment.assetClass}
              className="allocation-bar__segment"
              style={{ width: `${pct}%`, backgroundColor: bg }}
              title={`${segment.assetClass}: ${pct}%`}
            >
              {pct >= 10 && <span className="allocation-bar__text">{segment.assetClass}</span>}
            </div>
          );
        })}
      </div>

      {showLabels && (
        <div className="allocation-legend">
          {segments.map((segment) => {
            const bg = segment.color || ASSET_COLORS[segment.assetClass] || '#94a3b8';
            return (
              <div key={segment.assetClass} className="allocation-legend__item">
                <span className="allocation-legend__dot" style={{ backgroundColor: bg }} />
                <span className="allocation-legend__name">{segment.assetClass}</span>
                <span className="allocation-legend__value">{segment.targetPct}%</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
